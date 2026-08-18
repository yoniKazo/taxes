import { useEffect, useRef, useState } from 'react';
import { createTestRun } from '../api/client.js';

// v1 של ה-Test Lab תמיד מריץ answer() של ה-agent "qa" (ראו docstring
// api/routes/test_runs.py) -- agent_name אחר יגרום לרשומות judge/explainer
// להיכתב תחת אותו agent_name ולהתנגש עם רשומות ה-bookkeeping הפנימיות.
const RUNNABLE_AGENT_NAMES = new Set(['qa']);

export default function RunForm({ agents, questions, onRunCreated }) {
  const runnableAgents = agents.filter((agent) => RUNNABLE_AGENT_NAMES.has(agent.name));
  const [agentName, setAgentName] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [label, setLabel] = useState('');
  const [selectedQuestionIds, setSelectedQuestionIds] = useState(() => new Set());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const questionsInitialized = useRef(false);
  const agentInitialized = useRef(false);

  useEffect(() => {
    if (!questionsInitialized.current && questions.length > 0) {
      setSelectedQuestionIds(new Set(questions.map((question) => question.id)));
      questionsInitialized.current = true;
    }
  }, [questions]);

  useEffect(() => {
    if (!agentInitialized.current && runnableAgents.length > 0) {
      applyAgentDefaults(runnableAgents[0]);
      agentInitialized.current = true;
    }
  }, [runnableAgents]);

  function applyAgentDefaults(agent) {
    if (!agent) {
      return;
    }
    setAgentName(agent.name);
    setTemperature(agent.default_temperature);
    setSystemPrompt(agent.default_system_prompt);
  }

  function handleAgentChange(name) {
    const agent = runnableAgents.find((candidate) => candidate.name === name);
    applyAgentDefaults(agent);
  }

  function toggleQuestion(id) {
    setSelectedQuestionIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function selectAllQuestions() {
    setSelectedQuestionIds(new Set(questions.map((question) => question.id)));
  }

  function clearAllQuestions() {
    setSelectedQuestionIds(new Set());
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const run = await createTestRun({
        agent_name: agentName,
        model: null,
        temperature,
        system_prompt: systemPrompt,
        question_ids: Array.from(selectedQuestionIds),
        label,
      });
      onRunCreated?.(run);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="card run-form" onSubmit={handleSubmit}>
      <h2>הרצה חדשה</h2>
      {error && <p className="explanation-error">{error}</p>}

      <div className="field-grid">
        <div>
          <label htmlFor="run-agent">Agent</label>
          <select
            id="run-agent"
            value={agentName}
            onChange={(event) => handleAgentChange(event.target.value)}
          >
            {runnableAgents.map((agent) => (
              <option key={agent.name} value={agent.name}>
                {agent.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="run-label">שם ניסוי</label>
          <input
            id="run-label"
            type="text"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder='למשל: "בלי בולרפלייט"'
          />
        </div>
      </div>

      <div>
        <label htmlFor="run-temperature">טמפרטורה: {temperature}</label>
        <input
          id="run-temperature"
          type="range"
          min="0"
          max="1.5"
          step="0.1"
          value={temperature}
          onChange={(event) => setTemperature(Number(event.target.value))}
        />
      </div>

      <div>
        <label htmlFor="run-system-prompt">פרומפט מערכת</label>
        <textarea
          id="run-system-prompt"
          rows={4}
          style={{ width: '100%' }}
          value={systemPrompt}
          onChange={(event) => setSystemPrompt(event.target.value)}
        />
      </div>

      <div>
        <div className="form-actions">
          <label style={{ margin: 0 }}>שאלות לבדיקה</label>
          <button type="button" onClick={selectAllQuestions}>
            בחר הכל
          </button>
          <button type="button" onClick={clearAllQuestions}>
            נקה בחירה
          </button>
        </div>
        <div className="question-checklist">
          {questions.map((question) => (
            <label key={question.id} className="question-checkbox-row">
              <input
                type="checkbox"
                checked={selectedQuestionIds.has(question.id)}
                onChange={() => toggleQuestion(question.id)}
              />
              {question.question_text}
            </label>
          ))}
        </div>
      </div>

      <div className="form-actions">
        <button
          type="submit"
          className="primary"
          disabled={submitting || !agentName || selectedQuestionIds.size === 0}
        >
          {submitting ? 'מריץ...' : 'הרץ'}
        </button>
      </div>
    </form>
  );
}
