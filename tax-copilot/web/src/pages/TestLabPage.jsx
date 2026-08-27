import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ClipboardList, Database, Gavel, History, ListChecks, Play, Scale } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import {
  getActiveRubric, getTestRun, listAgents, listTestQuestions, listTestRuns, runJudgeAsync,
} from '../api/client.js';
import AgreementPanel from '../components/lab/AgreementPanel.jsx';
import DatasetPanel from '../components/lab/DatasetPanel.jsx';
import ResultsTable from '../components/lab/ResultsTable.jsx';
import RubricPanel from '../components/lab/RubricPanel.jsx';
import RunForm from '../components/lab/RunForm.jsx';
import RunHistoryPanel from '../components/lab/RunHistoryPanel.jsx';
import ProgressBar from '../components/ui/ProgressBar.jsx';
import Panel from '../components/ui/Panel.jsx';
import PanelPicker from '../components/ui/PanelPicker.jsx';
import ProcessExplainer from '../components/ui/ProcessExplainer.jsx';
import { LAB_EXPLAINERS } from '../constants/labExplainers.js';
import { JUDGE_MODEL_OPTIONS } from '../constants/labModels.js';
import { useJob } from '../hooks/useJob.js';
import { usePanelPrefs } from '../hooks/usePanelPrefs.js';

// The run form comes first now. Rubric and dataset are long tables that used to
// sit above it, pushing the page's primary action below the fold, so they start
// folded.
const PANELS = [
  { id: 'run', title: 'הרצה חדשה', icon: Play, cost: 'עולה קריאות' },
  { id: 'results', title: 'תוצאות הריצה', icon: ClipboardList },
  { id: 'agreement', title: 'הסכמת human מול judge', icon: Scale },
  { id: 'history', title: 'היסטוריית ריצות', icon: History },
  { id: 'dataset', title: 'דאטהסט שאלות', icon: Database },
  { id: 'rubric', title: 'רוברייק פעילה', icon: ListChecks },
];

export default function TestLabPage() {
  const prefs = usePanelPrefs('lab', PANELS);
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  // Deep-linkable: /lab?run=12 reopens that run.
  const selectedRunId = searchParams.get('run') ? Number(searchParams.get('run')) : null;
  const selectRun = useCallback(
    (id) => setSearchParams((current) => {
      const next = new URLSearchParams(current);
      if (id == null) next.delete('run');
      else next.set('run', String(id));
      return next;
    }, { replace: true }),
    [setSearchParams],
  );

  const agents = useQuery({
    queryKey: ['agents'],
    queryFn: listAgents,
  });
  const rubric = useQuery({ queryKey: ['rubric'], queryFn: getActiveRubric });
  const questions = useQuery({ queryKey: ['test-questions'], queryFn: () => listTestQuestions() });
  const runs = useQuery({ queryKey: ['test-runs'], queryFn: listTestRuns });
  const run = useQuery({
    queryKey: ['test-run', selectedRunId],
    queryFn: () => getTestRun(selectedRunId),
    enabled: selectedRunId != null,
  });

  const [judgeModel, setJudgeModel] = useState(JUDGE_MODEL_OPTIONS[0].value);
  const [compareWith, setCompareWith] = useState(null);
  const compareRun = useQuery({
    queryKey: ['test-run', compareWith],
    queryFn: () => getTestRun(compareWith),
    enabled: compareWith != null,
  });

  const judgeJob = useJob({
    start: () => runJudgeAsync(selectedRunId, judgeModel),
    successMessage: 'השיפוט הסתיים.',
    onDone: () => {
      queryClient.invalidateQueries({ queryKey: ['test-run', selectedRunId] });
      queryClient.invalidateQueries({ queryKey: ['test-runs'] });
      queryClient.invalidateQueries({ queryKey: ['agreement', selectedRunId] });
    },
  });

  const ratableCriteria = useMemo(
    () => (rubric.data?.criteria ?? []).filter((criterion) => !criterion.is_programmatic),
    [rubric.data],
  );

  const onRunFinished = useCallback(
    (runId) => {
      queryClient.invalidateQueries({ queryKey: ['test-runs'] });
      selectRun(runId);
    },
    [queryClient, selectRun],
  );

  const panelProps = (id) => ({
    collapsed: prefs.isCollapsed(id),
    onToggleCollapsed: () => prefs.toggleCollapsed(id),
    onHide: () => prefs.toggleVisible(id),
  });

  const judged = (run.data?.results ?? []).some((result) => result.judge_final_score);

  return (
    <div className="app-main">
      <div className="row between" style={{ marginBlockEnd: 'var(--space-4)' }}>
        <div>
          <h1>מעבדת בדיקות AI</h1>
          <p className="muted" style={{ margin: 0 }}>
            מטלה 2 — רוברייק, הרצות, ושיפוט אוטומטי מול דירוג אנושי
          </p>
        </div>
        <PanelPicker panels={PANELS} prefs={prefs} />
      </div>

      {prefs.isVisible('run') ? (
        <Panel
          title="הרצה חדשה"
          icon={Play}
          {...panelProps('run')}
          loading={agents.isPending || questions.isPending}
          error={agents.error?.message ?? questions.error?.message}
        >
          <ProcessExplainer id="run" {...LAB_EXPLAINERS.run} />
          <RunForm
            agents={agents.data ?? []}
            questions={questions.data ?? []}
            onRunFinished={onRunFinished}
            judgeModel={judgeModel}
            onJudgeModelChange={setJudgeModel}
          />
        </Panel>
      ) : null}

      {prefs.isVisible('results') && selectedRunId != null ? (
        <Panel
          title="תוצאות הריצה"
          subtitle={run.data?.label || `ריצה #${selectedRunId}`}
          icon={ClipboardList}
          {...panelProps('results')}
          loading={run.isPending}
          error={run.error?.message}
          actions={
            <div className="row">
              <select
                aria-label="AI שופט"
                value={judgeModel}
                onChange={(event) => setJudgeModel(event.target.value)}
                disabled={judgeJob.running}
              >
                {JUDGE_MODEL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
              <button type="button" onClick={() => judgeJob.start()} disabled={judgeJob.running}>
                <Gavel size={14} aria-hidden />
                {judgeJob.running ? 'שופט…' : judged ? 'שפוט את מה שנותר' : 'הפעל judge'}
              </button>
              <span className="cost-hint">~1 קריאה לשורה</span>
            </div>
          }
        >
          <ProcessExplainer id="results" {...LAB_EXPLAINERS.results} />
          {judgeJob.running ? (
            <div style={{ marginBlockEnd: 'var(--space-4)' }}>
              <ProgressBar
                phase={judgeJob.job?.phase ?? 'מתחיל…'}
                done={judgeJob.job?.done ?? 0}
                total={judgeJob.job?.total ?? 0}
                etaSeconds={estimateEta(judgeJob.job, 17)}
                onCancel={judgeJob.cancel}
              />
              <p className="muted" style={{ marginBlockStart: 'var(--space-2)' }}>
                ביטול עוצר אחרי השורה הנוכחית. הפעלה חוזרת ממשיכה מאיפה שהפסיקה — השיפוט
                מדלג על שורות שכבר שופטו.
              </p>
            </div>
          ) : null}

          <ResultsTable
            run={run.data}
            compareRun={compareWith != null ? compareRun.data : null}
            criteria={ratableCriteria}
          />
        </Panel>
      ) : null}

      {prefs.isVisible('agreement') && selectedRunId != null ? (
        <Panel title="הסכמת human מול judge" icon={Scale} {...panelProps('agreement')}>
          <ProcessExplainer id="agreement" {...LAB_EXPLAINERS.agreement} />
          <AgreementPanel testRunId={selectedRunId} />
        </Panel>
      ) : null}

      {prefs.isVisible('history') ? (
        <Panel
          title="היסטוריית ריצות"
          icon={History}
          {...panelProps('history')}
          loading={runs.isPending}
          error={runs.error?.message}
        >
          <ProcessExplainer id="history" {...LAB_EXPLAINERS.history} />
          <RunHistoryPanel
            runs={runs.data ?? []}
            selectedRunId={selectedRunId}
            compareWith={compareWith}
            onSelect={selectRun}
            onCompare={setCompareWith}
          />
        </Panel>
      ) : null}

      {prefs.isVisible('dataset') ? (
        <Panel
          title="דאטהסט שאלות"
          icon={Database}
          {...panelProps('dataset')}
          loading={questions.isPending}
          error={questions.error?.message}
        >
          <ProcessExplainer id="dataset" {...LAB_EXPLAINERS.dataset} />
          <DatasetPanel questions={questions.data ?? []} />
        </Panel>
      ) : null}

      {prefs.isVisible('rubric') ? (
        <Panel
          title="רוברייק פעילה"
          icon={ListChecks}
          {...panelProps('rubric')}
          loading={rubric.isPending}
          error={rubric.error?.message}
        >
          <ProcessExplainer id="rubric" {...LAB_EXPLAINERS.rubric} />
          <RubricPanel rubric={rubric.data} />
        </Panel>
      ) : null}
    </div>
  );
}

/** Rough ETA from the throttle floor: each item costs roughly `perItem` seconds. */
function estimateEta(job, perItem) {
  if (!job?.total) return null;
  return Math.max(0, (job.total - job.done) * perItem);
}
