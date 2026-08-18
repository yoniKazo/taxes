function makeEmptyJob() {
  return { gross_salary: '', label: '' };
}

export default function JobsForm({ jobs, onChange }) {
  function updateJob(index, field, value) {
    const next = jobs.slice();
    next[index] = { ...next[index], [field]: value };
    onChange(next);
  }

  function addJob() {
    onChange([...jobs, makeEmptyJob()]);
  }

  function removeJob(index) {
    onChange(jobs.filter((_, i) => i !== index));
  }

  return (
    <div className="jobs-form">
      <h2>עבודות</h2>
      {jobs.map((job, index) => (
        <div className="field-grid" key={index}>
          <div>
            <label htmlFor={`job-salary-${index}`}>שכר ברוטו שנתי</label>
            <input
              id={`job-salary-${index}`}
              type="number"
              min="0"
              step="1"
              value={job.gross_salary}
              onChange={(event) => updateJob(index, 'gross_salary', event.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor={`job-label-${index}`}>תיאור (אופציונלי)</label>
            <input
              id={`job-label-${index}`}
              type="text"
              value={job.label}
              onChange={(event) => updateJob(index, 'label', event.target.value)}
              placeholder="למשל: עבודה ראשית"
            />
          </div>
          <div className="form-actions">
            <button
              type="button"
              onClick={() => removeJob(index)}
              disabled={jobs.length <= 1}
            >
              הסר עבודה
            </button>
          </div>
        </div>
      ))}
      <div className="form-actions">
        <button type="button" onClick={addJob}>
          הוסף עבודה
        </button>
      </div>
    </div>
  );
}
