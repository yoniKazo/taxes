import { Bot, Play, Search, Wrench } from 'lucide-react';
import { useMemo, useState } from 'react';

import { TOOL_ABLATION } from '../../constants/agentLabExplainers.js';

const TOOL_ICONS = { search_tax_corpus: Search, calculator: Wrench, calculate_tax_refund: Wrench };

export default function PlaygroundPanel({
  tasks, tools, configs, onRun, isPending, error, result,
}) {
  const [taskId, setTaskId] = useState('');
  const [freeText, setFreeText] = useState('');
  const [config, setConfig] = useState('agent');
  const [configId, setConfigId] = useState('canonical');
  const [enabledTools, setEnabledTools] = useState(() => new Set(tools.map((t) => t.name)));
  const [breakTool, setBreakTool] = useState('');

  const activeConfig = useMemo(
    () => configs.find((c) => c.id === configId) ?? configs[0],
    [configs, configId],
  );

  const taskText = taskId ? tasks.find((t) => t.task_id === taskId)?.task ?? '' : freeText;

  const toggleTool = (name) => {
    setEnabledTools((current) => {
      const next = new Set(current);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const submit = (event) => {
    event.preventDefault();
    if (!taskText.trim()) return;
    onRun({
      task: taskText,
      config,
      enabled_tools: config === 'agent' ? [...enabledTools] : null,
      break_tool: breakTool || null,
      use_evaluator_optimizer: true,
      model: activeConfig?.model ?? 'claude-haiku-4-5',
      judge_model: activeConfig?.judge_model ?? 'claude-sonnet-5',
      system_prompt: activeConfig?.system_prompt ?? null,
    });
  };

  return (
    <form onSubmit={submit}>
      <div className="field-grid">
        <div>
          <label htmlFor="pg-task-select">משימה ממערך המשימות</label>
          <select id="pg-task-select" value={taskId} onChange={(e) => setTaskId(e.target.value)}>
            <option value="">— קלט חופשי —</option>
            {tasks.map((t) => (
              <option key={t.task_id} value={t.task_id}>{t.task_id} · {t.type}</option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="pg-config">קונפיגורציה</label>
          <select id="pg-config" value={config} onChange={(e) => setConfig(e.target.value)}>
            <option value="agent">Agent (LangGraph + evaluator-optimizer)</option>
            <option value="rag">RAG (הבייסליין הקפוא, מטלה 3)</option>
          </select>
        </div>

        {config === 'agent' ? (
          <div>
            <label htmlFor="pg-agent-config">קונפיגורציית agent</label>
            <select id="pg-agent-config" value={configId} onChange={(e) => setConfigId(e.target.value)}>
              {configs.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            {activeConfig ? (
              <div className="field-hint">agent: {activeConfig.model} · judge: {activeConfig.judge_model}</div>
            ) : null}
          </div>
        ) : null}

        {config === 'agent' ? (
          <div>
            <label htmlFor="pg-break-tool">שבור tool בכוונה (Task 3.5)</label>
            <select id="pg-break-tool" value={breakTool} onChange={(e) => setBreakTool(e.target.value)}>
              <option value="">— אף אחד —</option>
              {tools.map((t) => (
                <option key={t.name} value={t.name}>{t.name}</option>
              ))}
            </select>
          </div>
        ) : null}
      </div>

      {!taskId ? (
        <div style={{ marginBlockStart: 'var(--space-4)' }}>
          <label htmlFor="pg-free-text">משימה (קלט חופשי)</label>
          <textarea
            id="pg-free-text"
            rows={2}
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            placeholder='למשל: "כמה מס רכישה אשלם על דירה שנייה בשווי 4,000,000 ₪?"'
          />
        </div>
      ) : (
        <p className="muted" style={{ marginBlockStart: 'var(--space-2)' }}>{taskText}</p>
      )}

      {config === 'agent' ? (
        <div style={{ marginBlockStart: 'var(--space-4)' }}>
          <strong>Tools זמינים ל-agent</strong>
          <div className="row" style={{ marginBlockStart: 'var(--space-2)' }}>
            {tools.map((t) => {
              const Icon = TOOL_ICONS[t.name] ?? Bot;
              return (
                <label key={t.name} className="checklist-row" style={{ display: 'inline-flex', width: 'auto' }}>
                  <input
                    type="checkbox"
                    checked={enabledTools.has(t.name)}
                    onChange={() => toggleTool(t.name)}
                  />
                  <Icon size={14} aria-hidden />
                  <span>{t.name}</span>
                </label>
              );
            })}
          </div>

          <details className="panel-note info" style={{ marginBlockStart: 'var(--space-3)' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
              מה קורה בתהליך עם כל הכלים, ומה נשבר כשכלי חסר
            </summary>
            <p style={{ marginBlockStart: 'var(--space-2)' }}>{TOOL_ABLATION.all}</p>
            <p className="muted">{TOOL_ABLATION.note}</p>
            <div className="checklist" style={{ marginBlockStart: 'var(--space-2)' }}>
              {TOOL_ABLATION.tools.map((t) => (
                <div key={t.name} className="checklist-row" style={{ display: 'block' }}>
                  <div>
                    <strong>בלי {t.name}</strong>
                    {enabledTools.has(t.name) ? null : <span className="muted"> · כרגע מכובה</span>}
                  </div>
                  <div className="muted">{t.without}</div>
                </div>
              ))}
            </div>
          </details>
        </div>
      ) : null}

      <div className="row" style={{ marginBlockStart: 'var(--space-4)' }}>
        <button type="submit" className="primary" disabled={isPending || !taskText.trim()}>
          <Play size={15} aria-hidden />
          {isPending ? 'מריץ…' : 'הרץ'}
        </button>
        {error ? <span style={{ color: 'var(--danger-fg)' }}>{error}</span> : null}
      </div>

      {result ? <PlaygroundResult result={result} /> : null}
    </form>
  );
}

function PlaygroundResult({ result }) {
  return (
    <div style={{ marginBlockStart: 'var(--space-4)' }} className="panel-note info">
      <div className="row between">
        <strong>תשובה ({result.config === 'rag' ? 'RAG' : 'Agent'})</strong>
        <span className="cost-hint">
          {result.terminal_state} · {result.tool_calls ?? 0} קריאות tool
          {result.latency_ms ? ` · ${Math.round(result.latency_ms)}ms` : ''}
        </span>
      </div>
      <p style={{ whiteSpace: 'pre-wrap' }}>{result.answer}</p>

      {result.judge ? (
        <p className="muted">
          evaluator-optimizer: {result.judge.verdict} אחרי {result.judge.rounds + 1} סבב(ים) —{' '}
          {Object.entries(result.judge.ratings).map(([k, v]) => `${k}=${v}`).join(', ')}
        </p>
      ) : null}

      {result.steps?.length ? (
        <details style={{ marginBlockStart: 'var(--space-2)' }}>
          <summary>trace ({result.steps.length} צעדים)</summary>
          <div className="checklist" style={{ marginBlockStart: 'var(--space-2)' }}>
            {result.steps.map((step, i) => (
              <div key={i} className="checklist-row" style={{ display: 'block' }}>
                <div><strong>שלב {step.step}</strong>{step.tool ? ` — ${step.tool}` : ' — תשובה סופית'}</div>
                {step.thought ? <div className="muted">{step.thought}</div> : null}
                {step.input ? <div className="muted">קלט: {JSON.stringify(step.input)}</div> : null}
                {step.output ? <div className="muted">פלט: {step.output}</div> : null}
              </div>
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}
