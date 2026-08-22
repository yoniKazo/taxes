import { useMutation } from '@tanstack/react-query';
import { Briefcase, Calculator, FileText, Settings2 } from 'lucide-react';
import { useState } from 'react';

import { calculateTax } from '../api/client.js';
import ExplanationPanel from '../components/calc/ExplanationPanel.jsx';
import JobsForm from '../components/calc/JobsForm.jsx';
import ResultsPanel from '../components/calc/ResultsPanel.jsx';
import SharedFieldsForm from '../components/calc/SharedFieldsForm.jsx';
import ErrorBanner from '../components/ui/ErrorBanner.jsx';
import Panel from '../components/ui/Panel.jsx';
import PanelPicker from '../components/ui/PanelPicker.jsx';
import { usePanelPrefs } from '../hooks/usePanelPrefs.js';

const PANELS = [
  { id: 'jobs', title: 'עבודות', icon: Briefcase },
  { id: 'details', title: 'פרטים נוספים', icon: Settings2 },
  { id: 'results', title: 'תוצאות', icon: Calculator },
  { id: 'explanation', title: 'הסבר מילולי', icon: FileText, cost: 'עולה קריאה' },
];

let nextJobId = 1;
const makeJob = () => ({ id: nextJobId++, gross_salary: '', label: '' });

const INITIAL_SHARED_FIELDS = {
  gender: 'male',
  extra_credit_points: 0,
  pension_employee_pct: 0,
  keren_hishtalmut_monthly: 0,
  annual_donation: 0,
};

function buildPayload(jobs, sharedFields, includeExplanation) {
  return {
    jobs: jobs.map((job) => ({
      // המשתמש מזין שכר שנתי; calculate() מצפה לשכר ברוטו חודשי.
      gross_salary: (Number(job.gross_salary) || 0) / 12,
      label: job.label,
    })),
    gender: sharedFields.gender,
    extra_credit_points: Number(sharedFields.extra_credit_points) || 0,
    // השדה מוצג באחוזים (0-100); calculate() מצפה לשבר (0-1).
    pension_employee_pct: (Number(sharedFields.pension_employee_pct) || 0) / 100,
    keren_hishtalmut_monthly: Number(sharedFields.keren_hishtalmut_monthly) || 0,
    annual_donation: Number(sharedFields.annual_donation) || 0,
    include_explanation: includeExplanation,
  };
}

export default function CalculatorPage() {
  const prefs = usePanelPrefs('calculator', PANELS);
  const [jobs, setJobs] = useState(() => [makeJob()]);
  const [sharedFields, setSharedFields] = useState(INITIAL_SHARED_FIELDS);

  const wantsExplanation = prefs.isVisible('explanation');

  const calculate = useMutation({
    mutationFn: () => calculateTax(buildPayload(jobs, sharedFields, wantsExplanation)),
  });

  const panelProps = (id) => ({
    collapsed: prefs.isCollapsed(id),
    onToggleCollapsed: () => prefs.toggleCollapsed(id),
    onHide: () => prefs.toggleVisible(id),
  });

  const result = calculate.data;

  return (
    <div className="app-main narrow">
      <div className="row between" style={{ marginBlockEnd: 'var(--space-4)' }}>
        <div>
          <h1>מחשבון החזר מס</h1>
          <p className="muted" style={{ margin: 0 }}>שכירים · שנת מס 2026</p>
        </div>
        <PanelPicker panels={PANELS} prefs={prefs} />
      </div>

      <ErrorBanner message={calculate.error?.message} onRetry={() => calculate.mutate()} />

      <form
        onSubmit={(event) => {
          event.preventDefault();
          calculate.mutate();
        }}
      >
        {prefs.isVisible('jobs') ? (
          <Panel title="עבודות" icon={Briefcase} {...panelProps('jobs')}>
            <JobsForm jobs={jobs} onChange={setJobs} makeJob={makeJob} />
          </Panel>
        ) : null}

        {prefs.isVisible('details') ? (
          <Panel title="פרטים נוספים" icon={Settings2} {...panelProps('details')}>
            <SharedFieldsForm values={sharedFields} onChange={setSharedFields} />
          </Panel>
        ) : null}

        <div className="row" style={{ marginBlockEnd: 'var(--space-4)' }}>
          <button type="submit" className="primary" disabled={calculate.isPending}>
            <Calculator size={15} aria-hidden />
            {calculate.isPending ? 'מחשב…' : 'חשב מס'}
          </button>
          {wantsExplanation ? <span className="cost-hint">כולל הסבר · קריאה 1</span> : null}
        </div>
      </form>

      {prefs.isVisible('results') && (result || calculate.isPending) ? (
        <Panel
          title="תוצאות"
          icon={Calculator}
          {...panelProps('results')}
          loading={calculate.isPending}
          skeletonRows={4}
        >
          <ResultsPanel result={result} />
        </Panel>
      ) : null}

      {wantsExplanation && (result || calculate.isPending) ? (
        <Panel title="הסבר מילולי" icon={FileText} {...panelProps('explanation')}>
          <ExplanationPanel
            loading={calculate.isPending}
            explanation={result?.explanation}
            explanationError={result?.explanation_error}
          />
        </Panel>
      ) : null}
    </div>
  );
}
