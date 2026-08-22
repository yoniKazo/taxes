const WIDTHS = ['100%', '92%', '78%', '86%', '70%'];

/** Shaped placeholder while data loads -- replaces the bare "טוען..." text. */
export default function Skeleton({ rows = 3 }) {
  return (
    <div aria-busy="true" aria-live="polite">
      <span className="muted" style={{ position: 'absolute', inset: 'auto', clip: 'rect(0 0 0 0)' }}>
        טוען…
      </span>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton" style={{ width: WIDTHS[i % WIDTHS.length] }} />
      ))}
    </div>
  );
}
