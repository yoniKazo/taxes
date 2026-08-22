import { useQueryClient } from '@tanstack/react-query';
import { Play, Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { createTestRunAsync } from '../../api/client.js';
import { useJob } from '../../hooks/useJob.js';
import ProgressBar from '../ui/ProgressBar.jsx';

// v1 always runs the qa call shape, so offering other agents would produce rows
// whose bookkeeping says one thing and whose prompt shape says another.
const RUNNABLE_AGENTS = new Set(['qa']);

// Each question is one throttled call; the server sleeps 4s between them.
const SECONDS_PER_QUESTION = 5;

export default function RunForm({ agents, questions, onRunFinished }) {
  const queryClient = useQueryClient();

  // useMemo, not a ref latch: this used to be recomputed on every render while
  // also being an effect dependency, and two useRefs existed purely to stop the
  // resulting infinite loop.
  const runnableAgents = useMemo(
    () => agents.filter((agent) => RUNNABLE_AGENTS.has(agent.name)),
    [agents],
  );

  const [agentName, setAgentName] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [label, setLabel] = useState('');
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [filter, setFilter] = useState('');
  const [touchedSelection, setTouchedSelection] = useState(false);

  useEffect(() => {
    if (agentName || runnableAgents.length === 0) return;
    const first = runnableAgents[0];
    setAgentName(first.name);
    setTemperature(first.default_temperature);
    setSystemPrompt(first.default_system_prompt);
  }, [runnableAgents, agentName]);

  useEffect(() => {
    if (touchedSelection || questions.length === 0) return;
    setSelectedIds(new Set(questions.map((question) => question.id)));
  }, [questions, touchedSelection]);

  const job = useJob({
    start: () => createTestRunAsync({
      agent_name: agentName,
      model: null,
      temperature,
      system_prompt: systemPrompt,
      question_ids: [...selectedIds],
      label,
    }),
    successMessage: 'ההרצה הסתיימה.',
    onDone: (result) => {
      queryClient.invalidateQueries({ queryKey: ['test-runs'] });
      if (result?.run_id) onRunFinished(result.run_id);
    },
  });

  const grouped = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    const matching = questions.filter(
      (question) =>
        !needle ||
        question.question_text.toLowerCase().includes(needle) ||
        (question.category ?? '').toLowerCase().includes(needle),
    );
    return matching.reduce((acc, question) => {
      const key = question.category ?? 'ללא קטגוריה';
      (acc[key] ??= []).push(question);
      return acc;
    }, {});
  }, [questions, filter]);

  const toggle = (id) => {
    setTouchedSelection(true);
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const setAll = (ids) => {
    setTouchedSelection(true);
    setSelectedIds(new Set(ids));
  };

  const estimatedSeconds = selectedIds.size * SECONDS_PER_QUESTION;

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        job.start();
      }}
    >
      <div className="field-grid">
        <div>
          <label htmlFor="run-agent">Agent</label>
          <select
            id="run-agent"
            value={agentName}
            onChange={(event) => {
              const agent = runnableAgents.find((a) => a.name === event.target.value);
              setAgentName(event.target.value);
              if (agent) {
                setTemperature(agent.default_temperature);
                setSystemPrompt(agent.default_system_prompt);
              }
            }}
          >
            {runnableAgents.map((agent) => (
              <option key={agent.name} value={agent.name}>{agent.name}</option>
            ))}
          </select>
          {runnableAgents.length === 0 ? (
            <div className="field-hint" style={{ color: 'var(--danger-fg)' }}>
              לא נטענו agents מהשרת.
            </div>
          ) : null}
        </div>

        <div>
          <label htmlFor="run-label">שם הניסוי</label>
          <input
            id="run-label"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder='למשל: "בלי בולרפלייט"'
          />
          <div className="field-hint">מופיע בהיסטוריה — עוזר להשוות שתי ריצות</div>
        </div>

        <div>
          <label htmlFor="run-temperature">טמפרטורה: {temperature}</label>
          <input
            id="run-temperature"
            type="range"
            min={0}
            max={1.5}
            step={0.1}
            value={temperature}
            onChange={(event) => setTemperature(Number(event.target.value))}
          />
          <div className="field-hint">0 = דטרמיניסטי; גבוה יותר = מגוון יותר</div>
        </div>
      </div>

      <div style={{ marginBlockStart: 'var(--space-4)' }}>
        <label htmlFor="run-prompt">System prompt</label>
        <textarea
          id="run-prompt"
          rows={4}
          value={systemPrompt}
          onChange={(event) => setSystemPrompt(event.target.value)}
        />
      </div>

      <div style={{ marginBlockStart: 'var(--space-4)' }}>
        <div className="row between" style={{ marginBlockEnd: 'var(--space-2)' }}>
          <strong>נבחרו {selectedIds.size} מתוך {questions.length} שאלות</strong>
          <div className="row">
            <button type="button" className="ghost" onClick={() => setAll(questions.map((q) => q.id))}>
              בחר הכל
            </button>
            <button type="button" className="ghost" onClick={() => setAll([])}>נקה בחירה</button>
          </div>
        </div>

        <div className="row" style={{ marginBlockEnd: 'var(--space-2)' }}>
          <Search size={15} aria-hidden style={{ color: 'var(--text-muted)' }} />
          <input
            type="search"
            className="grow search-input"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="סנן שאלות…"
            aria-label="סנן שאלות"
          />
        </div>

        <div className="checklist">
          {Object.entries(grouped).map(([category, items]) => (
            <div key={category}>
              <div className="checklist-group-title">{category} ({items.length})</div>
              {items.map((question) => (
                <label key={question.id} className="checklist-row">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(question.id)}
                    onChange={() => toggle(question.id)}
                  />
                  <span>{question.question_text}</span>
                </label>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="row" style={{ marginBlockStart: 'var(--space-4)' }}>
        <button
          type="submit"
          className="primary"
          disabled={job.running || !agentName || selectedIds.size === 0}
        >
          <Play size={15} aria-hidden />
          {job.running ? 'מריץ…' : `הרץ ${selectedIds.size} שאלות`}
        </button>
        <span className="muted">
          {selectedIds.size} קריאות · ~{Math.ceil(estimatedSeconds / 60)} דקות
        </span>
      </div>

      {job.running ? (
        <div style={{ marginBlockStart: 'var(--space-4)' }}>
          <ProgressBar
            phase={job.job?.phase ?? 'מתחיל…'}
            done={job.job?.done ?? 0}
            total={job.job?.total ?? 0}
            etaSeconds={
              job.job?.total ? (job.job.total - job.job.done) * SECONDS_PER_QUESTION : null
            }
            onCancel={job.cancel}
          />
        </div>
      ) : null}
    </form>
  );
}
