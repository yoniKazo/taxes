import { Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';

const ALL_TOOLS = ['search_tax_corpus', 'calculator', 'calculate_tax_refund'];

// claude-haiku-4-5 / claude-sonnet-5 הם ברירת המחדל של המטלה (src/model_providers.py).
// Gemini הוא אופציה לבקרת עלות — לא תחליף שקט להשוואה הרשמית של Task 5.
const AGENT_MODEL_OPTIONS = [
  { value: 'claude-haiku-4-5', label: 'claude-haiku-4-5 (ברירת מחדל, שיעורי בית)' },
  { value: 'claude-sonnet-5', label: 'claude-sonnet-5 (שדרוג — ניסוי Task 6)' },
  { value: 'gemini-flash-lite-latest', label: 'gemini-flash-lite-latest (חינמי — בקרת עלות)' },
];
const JUDGE_MODEL_OPTIONS = [
  { value: 'claude-sonnet-5', label: 'claude-sonnet-5 (ברירת מחדל, שיעורי בית)' },
  { value: 'gemini-3.1-flash-lite', label: 'gemini-3.1-flash-lite (חינמי — בקרת עלות)' },
];

export default function ConfigsPanel({ configs, onAdd, onDelete, experiments }) {
  const [name, setName] = useState('');
  const [model, setModel] = useState('claude-haiku-4-5');
  const [judgeModel, setJudgeModel] = useState('claude-sonnet-5');
  const [enabledTools, setEnabledTools] = useState(() => new Set(ALL_TOOLS));
  const [systemPrompt, setSystemPrompt] = useState('');

  const toggleTool = (toolName) => {
    setEnabledTools((current) => {
      const next = new Set(current);
      if (next.has(toolName)) next.delete(toolName);
      else next.add(toolName);
      return next;
    });
  };

  const submit = (event) => {
    event.preventDefault();
    if (!name.trim() || enabledTools.size === 0) return;
    onAdd({
      name, model, judge_model: judgeModel, enabled_tools: [...enabledTools],
      system_prompt: systemPrompt.trim() || null,
    });
    setName('');
    setSystemPrompt('');
  };

  return (
    <div>
      <form onSubmit={submit} style={{ marginBlockEnd: 'var(--space-4)' }}>
        <div className="field-grid">
          <div>
            <label htmlFor="cfg-name">שם הקונפיגורציה</label>
            <input id="cfg-name" value={name} onChange={(e) => setName(e.target.value)}
                   placeholder='למשל: "בלי calculator"' />
          </div>
          <div>
            <label htmlFor="cfg-model">מודל ה-agent</label>
            <select id="cfg-model" value={model} onChange={(e) => setModel(e.target.value)}>
              {AGENT_MODEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="cfg-judge-model">מודל ה-judge (evaluator-optimizer)</label>
            <select id="cfg-judge-model" value={judgeModel} onChange={(e) => setJudgeModel(e.target.value)}>
              {JUDGE_MODEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ marginBlockStart: 'var(--space-2)' }}>
          <strong>tools זמינים</strong>
          <div className="row">
            {ALL_TOOLS.map((toolName) => (
              <label key={toolName} className="checklist-row" style={{ display: 'inline-flex', width: 'auto' }}>
                <input type="checkbox" checked={enabledTools.has(toolName)} onChange={() => toggleTool(toolName)} />
                <span>{toolName}</span>
              </label>
            ))}
          </div>
        </div>

        <div style={{ marginBlockStart: 'var(--space-2)' }}>
          <label htmlFor="cfg-prompt">system prompt מותאם (ריק = הפרומפט הקנוני)</label>
          <textarea id="cfg-prompt" rows={2} value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} />
        </div>

        <button type="submit" className="primary" style={{ marginBlockStart: 'var(--space-2)' }}>
          <Plus size={15} aria-hidden />
          הוסף קונפיגורציה
        </button>
      </form>

      <div className="checklist">
        {configs.map((cfg) => (
          <div key={cfg.id} className="checklist-row row between">
            <div>
              <strong>{cfg.name}</strong>
              <div className="muted">
                agent: {cfg.model} · judge: {cfg.judge_model} · {cfg.enabled_tools.join(', ')}
                {cfg.is_canonical ? ' · קנונית' : ''}
              </div>
            </div>
            {!cfg.is_canonical ? (
              <button type="button" className="ghost" onClick={() => onDelete(cfg.id)}>
                <Trash2 size={14} aria-hidden />
              </button>
            ) : null}
          </div>
        ))}
      </div>

      <div style={{ marginBlockStart: 'var(--space-4)' }}>
        <strong>ניסויי Task 6 (השוואה מלאה מול הקונפיגורציה הקנונית)</strong>
        {experiments.available ? (
          <div className="checklist" style={{ marginBlockStart: 'var(--space-2)' }}>
            {experiments.experiments.map((exp, i) => (
              <div key={i} className="checklist-row" style={{ display: 'block' }}>
                <div><strong>{exp.name}</strong></div>
                <div className="muted">השערה: {exp.hypothesis}</div>
                <div className="muted">מסקנה: {exp.conclusion}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">עדיין לא רצו ניסויי Task 6 (assignment4_experiments.py).</p>
        )}
      </div>
    </div>
  );
}
