import { useMemo, useState } from 'react';

const TYPE_LABELS = {
  multi_hop: 'multi_hop', no_tool: 'no_tool', unanswerable: 'unanswerable',
  tool_fails: 'tool_fails', single: 'single',
};

export default function TaskSetPanel({ tasks, onUseTask }) {
  const [filter, setFilter] = useState('all');

  const filtered = useMemo(
    () => (filter === 'all' ? tasks : tasks.filter((t) => t.type === filter)),
    [tasks, filter],
  );

  return (
    <div>
      <div className="row" style={{ marginBlockEnd: 'var(--space-2)' }}>
        <select value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="סנן לפי סוג">
          <option value="all">כל הסוגים ({tasks.length})</option>
          {Object.entries(TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label} ({tasks.filter((t) => t.type === value).length})
            </option>
          ))}
        </select>
      </div>

      <div className="checklist">
        {filtered.map((task) => (
          <div key={task.task_id} className="checklist-row" style={{ display: 'block' }}>
            <div className="row between">
              <strong>{task.task_id} · {task.type}{task.answerable === false ? ' · לא-ניתן-למענה' : ''}</strong>
              <button type="button" className="ghost" onClick={() => onUseTask(task.task_id)}>
                השתמש במגרש המשחקים
              </button>
            </div>
            <p style={{ marginBlockStart: 'var(--space-1)' }}>{task.task}</p>
            <p className="muted">success_criteria: {task.success_criteria}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
