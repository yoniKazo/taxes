export default function AnnotatedTracesPanel({ data }) {
  if (!data.available) {
    return <p className="muted">עדיין אין traces מוערים ב-assignment4/annotated_traces/.</p>;
  }

  return (
    <div className="checklist">
      {data.traces.map((trace) => (
        <details key={trace.name} className="checklist-row" style={{ display: 'block' }}>
          <summary><strong>{trace.name}</strong></summary>
          <pre style={{ whiteSpace: 'pre-wrap', marginBlockStart: 'var(--space-2)' }}>{trace.content}</pre>
        </details>
      ))}
    </div>
  );
}
