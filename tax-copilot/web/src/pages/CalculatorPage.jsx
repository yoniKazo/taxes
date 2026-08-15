import { useState } from 'react';
import JobsForm from '../components/JobsForm.jsx';
import SharedFieldsForm from '../components/SharedFieldsForm.jsx';
import ResultsPanel from '../components/ResultsPanel.jsx';
import ExplanationPanel from '../components/ExplanationPanel.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';
import { calculateTax } from '../api/client.js';

const INITIAL_JOBS = [{ gross_salary: '', label: '' }];

const INITIAL_SHARED_FIELDS = {
  gender: 'male',
  extra_credit_points: 0,
  pension_employee_pct: 0,
  keren_hishtalmut_monthly: 0,
  annual_donation: 0,
};

function buildPayload(jobs, sharedFields) {
  return {
    jobs: jobs.map((job) => ({
      gross_salary: Number(job.gross_salary) || 0,
      label: job.label,
    })),
    gender: sharedFields.gender,
    extra_credit_points: Number(sharedFields.extra_credit_points) || 0,
    pension_employee_pct: Number(sharedFields.pension_employee_pct) || 0,
    keren_hishtalmut_monthly: Number(sharedFields.keren_hishtalmut_monthly) || 0,
    annual_donation: Number(sharedFields.annual_donation) || 0,
    include_explanation: true,
  };
}

export default function CalculatorPage() {
  const [jobs, setJobs] = useState(INITIAL_JOBS);
  const [sharedFields, setSharedFields] = useState(INITIAL_SHARED_FIELDS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = buildPayload(jobs, sharedFields);
      const response = await calculateTax(payload);
      setResult(response);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="calculator-page">
      <ErrorBanner message={error} />
      <form onSubmit={handleSubmit}>
        <div className="card">
          <JobsForm jobs={jobs} onChange={setJobs} />
        </div>
        <div className="card">
          <SharedFieldsForm values={sharedFields} onChange={setSharedFields} />
        </div>
        <div className="form-actions">
          <button type="submit" className="primary" disabled={loading}>
            {loading ? 'מחשב...' : 'חשב מס'}
          </button>
        </div>
      </form>

      <ResultsPanel result={result} />
      {(loading || result) && (
        <ExplanationPanel
          loading={loading}
          explanation={result?.explanation}
          explanationError={result?.explanation_error}
        />
      )}
    </div>
  );
}
