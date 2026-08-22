/**
 * Progress for the operations that take minutes.
 *
 * `total` of 0 means the job is working but cannot count items yet (parsing the
 * corpus before embedding starts) -- that renders as an indeterminate sweep
 * rather than a bar frozen at zero, which reads as "stuck".
 */
export default function ProgressBar({ phase, done = 0, total = 0, etaSeconds, onCancel }) {
  const determinate = total > 0;
  const pct = determinate ? Math.min(100, Math.round((done / total) * 100)) : 0;

  return (
    <div className="progress">
      <div className="progress-track">
        <div
          className={determinate ? 'progress-fill' : 'progress-fill indeterminate'}
          style={determinate ? { width: `${pct}%` } : undefined}
          role="progressbar"
          aria-valuenow={determinate ? done : undefined}
          aria-valuemin={0}
          aria-valuemax={determinate ? total : undefined}
          aria-label={phase}
        />
      </div>
      <div className="progress-meta">
        <span>
          {phase}
          {determinate ? ` · ${done} מתוך ${total}` : ''}
          {etaSeconds != null && etaSeconds > 0 ? ` · נותרו ~${formatEta(etaSeconds)}` : ''}
        </span>
        {onCancel ? (
          <button type="button" className="ghost" onClick={onCancel}>
            בטל
          </button>
        ) : null}
      </div>
    </div>
  );
}

function formatEta(seconds) {
  if (seconds < 60) return `${Math.round(seconds)} שניות`;
  return `${Math.round(seconds / 60)} דקות`;
}
