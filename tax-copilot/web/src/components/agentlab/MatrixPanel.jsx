const TYPE_ORDER = ['single', 'multi_hop', 'no_tool', 'unanswerable', 'tool_fails'];

function fmtRate(rate) {
  return rate == null ? '—' : `${Math.round(rate * 100)}%`;
}

function fmtMs(ms) {
  return ms == null || Number.isNaN(ms) ? '—' : `${Math.round(ms)}ms`;
}

export default function MatrixPanel({ data }) {
  if (!data.available) {
    return (
      <p className="muted">
        המטריצה עדיין לא רצה. הריצו <code>python src/assignment4_eval_runner.py</code> מ-tax-copilot/
        (הרצה ארוכה — מאות קריאות בתשלום אמיתי, ראו plans/assignment4-plan.md לפני שמריצים בפעם הראשונה).
      </p>
    );
  }

  const byType = TYPE_ORDER
    .map((type) => ({
      type,
      rag: data.summary.find((r) => r.type === type && r.config === 'rag'),
      agent: data.summary.find((r) => r.type === type && r.config === 'agent'),
    }))
    .filter((row) => row.rag || row.agent);

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'right' }}>סוג משימה</th>
            <th style={{ textAlign: 'right' }}>הצלחה — RAG</th>
            <th style={{ textAlign: 'right' }}>הצלחה — Agent</th>
            <th style={{ textAlign: 'right' }}>latency ממוצע — RAG</th>
            <th style={{ textAlign: 'right' }}>latency ממוצע — Agent</th>
            <th style={{ textAlign: 'right' }}>tool calls ממוצע — Agent</th>
            <th style={{ textAlign: 'right' }}>n</th>
          </tr>
        </thead>
        <tbody>
          {byType.map((row) => (
            <tr key={row.type}>
              <td><strong>{row.type}</strong></td>
              <td>{row.rag ? fmtRate(row.rag.success_rate) : 'n/a'}</td>
              <td>{fmtRate(row.agent?.success_rate)}</td>
              <td>{row.rag ? fmtMs(row.rag.mean_latency_ms) : 'n/a'}</td>
              <td>{fmtMs(row.agent?.mean_latency_ms)}</td>
              <td>{row.agent?.mean_tool_calls?.toFixed(1) ?? '—'}</td>
              <td>{row.agent?.n ?? row.rag?.n ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
