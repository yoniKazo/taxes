import { Plus, Trash2 } from 'lucide-react';

/**
 * Jobs are keyed by a stable id, not by array index.
 *
 * With index keys, removing a middle row made React reuse the removed row's DOM
 * input for its successor -- the values appeared to shuffle.
 */
export default function JobsForm({ jobs, onChange, makeJob }) {
  const update = (id, field, value) =>
    onChange(jobs.map((job) => (job.id === id ? { ...job, [field]: value } : job)));

  return (
    <>
      {jobs.map((job, index) => (
        <div
          key={job.id}
          className="field-grid"
          style={{ marginBlockEnd: 'var(--space-4)', alignItems: 'end' }}
        >
          <div>
            <label htmlFor={`salary-${job.id}`}>שכר ברוטו שנתי</label>
            <input
              id={`salary-${job.id}`}
              type="number"
              min="0"
              required
              value={job.gross_salary}
              onChange={(event) => update(job.id, 'gross_salary', event.target.value)}
              placeholder="180000"
            />
            <div className="field-hint">₪ לשנה, לפני ניכויים</div>
          </div>

          <div>
            <label htmlFor={`label-${job.id}`}>כינוי (רשות)</label>
            <input
              id={`label-${job.id}`}
              value={job.label}
              onChange={(event) => update(job.id, 'label', event.target.value)}
              placeholder={index === 0 ? 'עבודה ראשית' : 'עבודה נוספת'}
            />
          </div>

          <div>
            <button
              type="button"
              className="ghost"
              disabled={jobs.length <= 1}
              onClick={() => onChange(jobs.filter((item) => item.id !== job.id))}
            >
              <Trash2 size={14} aria-hidden />
              הסר
            </button>
          </div>
        </div>
      ))}

      <button type="button" onClick={() => onChange([...jobs, makeJob()])}>
        <Plus size={15} aria-hidden />
        הוסף עבודה
      </button>
      <p className="muted" style={{ marginBlockStart: 'var(--space-3)' }}>
        שתי עבודות או יותר הן הסיבה השכיחה להחזר מס — כל מעסיק מנכה כאילו הוא היחיד.
      </p>
    </>
  );
}
