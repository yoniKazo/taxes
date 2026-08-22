export default function Stat({ label, value, caption, hero = false, tone }) {
  return (
    <div className={hero ? 'stat hero' : 'stat'}>
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={tone ? { color: `var(--${tone}-fg)` } : undefined}>
        {value}
      </div>
      {caption ? <div className="stat-caption">{caption}</div> : null}
    </div>
  );
}

/**
 * Similarity as a bar, not just a number.
 *
 * Fed the converted cosine similarity from the API -- FAISS's own output is an
 * L2 distance where lower is better, and binding a meter to that would draw the
 * best match as the emptiest bar.
 */
export function ScoreMeter({ score }) {
  if (score == null) {
    return <span className="muted" title="hybrid retrieval לא מחזיר ציון השוואתי">—</span>;
  }
  return (
    <div className="meter">
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${Math.max(0, Math.min(1, score)) * 100}%` }} />
      </div>
      <span className="meter-value">{score.toFixed(3)}</span>
    </div>
  );
}
