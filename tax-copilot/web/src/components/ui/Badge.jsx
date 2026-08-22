const VERDICT_LABELS = {
  good: 'טוב',
  ok: 'בינוני',
  bad: 'גרוע',
  pass: 'עבר',
  fail: 'נכשל',
};

/**
 * A verdict outside good/ok/bad used to render as an unstyled pill, because the
 * raw string was pasted straight into the class name. `neutral` is the fallback
 * so an unexpected value still looks like a badge.
 */
export default function Badge({ tone = 'neutral', children, title }) {
  const known = ['good', 'ok', 'bad', 'pass', 'fail', 'success', 'warning', 'danger', 'info',
    'neutral', 'partial', 'missing', 'complete', 'correct', 'refused', 'hallucinated'];
  const resolved = known.includes(tone) ? tone : 'neutral';
  return (
    <span className={`badge ${resolved}`} title={title}>
      {children}
    </span>
  );
}

export function VerdictBadge({ verdict, title }) {
  if (!verdict || verdict === 'N/A') return <span className="muted">—</span>;
  return (
    <Badge tone={verdict} title={title}>
      {VERDICT_LABELS[verdict] ?? verdict}
    </Badge>
  );
}
