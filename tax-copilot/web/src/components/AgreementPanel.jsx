import { useEffect, useState } from 'react';
import { getAgreement } from '../api/client.js';

export default function AgreementPanel({ testRunId }) {
  const [agreement, setAgreement] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!testRunId) {
      setAgreement(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getAgreement(testRunId)
      .then((data) => {
        if (!cancelled) {
          setAgreement(data);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [testRunId]);

  if (!testRunId) {
    return null;
  }

  return (
    <div className="card agreement-panel">
      <h2>הסכמת human/judge</h2>
      {loading && <p>טוען...</p>}
      {error && <p className="explanation-error">{error}</p>}

      {agreement && (
        <>
          <table>
            <thead>
              <tr>
                <th>קריטריון</th>
                <th>אחוז הסכמה</th>
                <th>מספר תשובות</th>
              </tr>
            </thead>
            <tbody>
              {agreement.per_criterion.map((row) => (
                <tr key={row.criterion}>
                  <td>{row.criterion}</td>
                  <td>{row.agreement_pct}%</td>
                  <td>{row.total}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>אי-הסכמות</h3>
          {agreement.disagreements.length === 0 ? (
            <p>אין אי-הסכמות.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>שאלה</th>
                  <th>קריטריון</th>
                  <th>ניקוד אנושי</th>
                  <th>ניקוד + הסבר judge</th>
                </tr>
              </thead>
              <tbody>
                {agreement.disagreements.map((row, index) => (
                  <tr key={`${row.llm_call_id}-${row.criterion}-${index}`}>
                    <td>{row.question_text}</td>
                    <td>{row.criterion}</td>
                    <td>
                      <span className={`badge ${row.human_verdict}`}>{row.human_verdict}</span>
                    </td>
                    <td>
                      <span className={`badge ${row.judge_verdict}`}>{row.judge_verdict}</span>{' '}
                      {row.judge_explanation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}
