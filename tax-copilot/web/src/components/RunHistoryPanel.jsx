function formatDate(value) {
  if (!value) {
    return '—';
  }
  try {
    return new Date(value).toLocaleString('he-IL');
  } catch {
    return value;
  }
}

export default function RunHistoryPanel({ runs, loading, error, selectedRunId, onSelect }) {
  return (
    <div className="card run-history-panel">
      <h2>היסטוריית ריצות</h2>
      {error && <p className="explanation-error">שגיאה בטעינת ההיסטוריה: {error}</p>}

      {loading ? (
        <p>טוען...</p>
      ) : runs.length === 0 ? (
        <p>אין עדיין ריצות.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>שם ניסוי</th>
              <th>Agent</th>
              <th>מודל</th>
              <th>טמפרטורה</th>
              <th>תאריך</th>
              <th>% pass</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr
                key={run.id}
                onClick={() => onSelect(run.id)}
                className={run.id === selectedRunId ? 'selected-row' : ''}
                style={{ cursor: 'pointer' }}
              >
                <td>{run.label || `ריצה #${run.id}`}</td>
                <td>{run.agent_name}</td>
                <td>{run.model}</td>
                <td>{run.temperature}</td>
                <td>{formatDate(run.created_at)}</td>
                <td>
                  {run.pass_percentage === null || run.pass_percentage === undefined
                    ? '—'
                    : `${run.pass_percentage}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
