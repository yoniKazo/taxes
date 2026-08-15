import { useCallback, useEffect, useState } from 'react';
import { listAgents, getActiveRubric, listTestQuestions, listTestRuns, getTestRun } from '../api/client.js';
import RubricPanel from '../components/RubricPanel.jsx';
import DatasetPanel from '../components/DatasetPanel.jsx';
import RunHistoryPanel from '../components/RunHistoryPanel.jsx';
import RunForm from '../components/RunForm.jsx';
import ResultsTable from '../components/ResultsTable.jsx';
import JudgeButton from '../components/JudgeButton.jsx';
import AgreementPanel from '../components/AgreementPanel.jsx';

export default function TestLabPage() {
  const [agents, setAgents] = useState([]);

  const [rubric, setRubric] = useState(null);
  const [rubricLoading, setRubricLoading] = useState(true);
  const [rubricError, setRubricError] = useState(null);

  const [questions, setQuestions] = useState([]);
  const [questionsLoading, setQuestionsLoading] = useState(true);
  const [questionsError, setQuestionsError] = useState(null);

  const [runs, setRuns] = useState([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [runsError, setRunsError] = useState(null);

  const [selectedRunId, setSelectedRunId] = useState(null);
  const [selectedRun, setSelectedRun] = useState(null);
  const [judgeRan, setJudgeRan] = useState(false);

  const refreshRubric = useCallback(() => {
    setRubricLoading(true);
    setRubricError(null);
    getActiveRubric()
      .then(setRubric)
      .catch((err) => setRubricError(err.message))
      .finally(() => setRubricLoading(false));
  }, []);

  const refreshQuestions = useCallback(() => {
    setQuestionsLoading(true);
    setQuestionsError(null);
    listTestQuestions()
      .then(setQuestions)
      .catch((err) => setQuestionsError(err.message))
      .finally(() => setQuestionsLoading(false));
  }, []);

  const refreshRuns = useCallback(() => {
    setRunsLoading(true);
    setRunsError(null);
    listTestRuns()
      .then(setRuns)
      .catch((err) => setRunsError(err.message))
      .finally(() => setRunsLoading(false));
  }, []);

  const loadRun = useCallback((id) => {
    setSelectedRunId(id);
    setJudgeRan(false);
    getTestRun(id)
      .then(setSelectedRun)
      .catch((err) => window.alert(`שגיאה בטעינת הריצה: ${err.message}`));
  }, []);

  useEffect(() => {
    listAgents().then(setAgents).catch(() => setAgents([]));
    refreshRubric();
    refreshQuestions();
    refreshRuns();
  }, [refreshRubric, refreshQuestions, refreshRuns]);

  function handleRunCreated(run) {
    setSelectedRunId(run.id);
    setSelectedRun(run);
    setJudgeRan(false);
    refreshRuns();
  }

  function handleRatingChanged() {
    if (selectedRunId) {
      getTestRun(selectedRunId).then(setSelectedRun);
      refreshRuns();
    }
  }

  function handleJudged() {
    setJudgeRan(true);
    if (selectedRunId) {
      getTestRun(selectedRunId).then(setSelectedRun);
      refreshRuns();
    }
  }

  const ratableCriteria = (rubric?.criteria || []).filter((criterion) => !criterion.is_programmatic);

  return (
    <div className="test-lab-page">
      <RubricPanel rubric={rubric} loading={rubricLoading} error={rubricError} onSaved={refreshRubric} />
      <DatasetPanel
        questions={questions}
        loading={questionsLoading}
        error={questionsError}
        onRefresh={refreshQuestions}
      />
      <RunHistoryPanel
        runs={runs}
        loading={runsLoading}
        error={runsError}
        selectedRunId={selectedRunId}
        onSelect={loadRun}
      />
      <RunForm agents={agents} questions={questions} onRunCreated={handleRunCreated} />

      {selectedRun && (
        <>
          <ResultsTable
            run={selectedRun}
            criteria={ratableCriteria}
            onRatingChanged={handleRatingChanged}
            judgeRan={judgeRan}
          />
          <JudgeButton testRunId={selectedRunId} onJudged={handleJudged} />
          <AgreementPanel testRunId={selectedRunId} />
        </>
      )}
    </div>
  );
}
