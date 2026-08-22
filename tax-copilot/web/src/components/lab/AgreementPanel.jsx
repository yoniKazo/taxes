import { useQuery } from '@tanstack/react-query';

import { getAgreement } from '../../api/client.js';
import Badge from '../ui/Badge.jsx';
import EmptyState from '../ui/EmptyState.jsx';
import ErrorBanner from '../ui/ErrorBanner.jsx';
import Skeleton from '../ui/Skeleton.jsx';

export default function AgreementPanel({ testRunId }) {
  const { data, isPending, error } = useQuery({
    queryKey: ['agreement', testRunId],
    queryFn: () => getAgreement(testRunId),
    enabled: testRunId != null,
  });

  if (error) return <ErrorBanner message={error.message} />;
  if (isPending) return <Skeleton rows={3} />;
  if (!data) return null;

  const measured = data.per_criterion.filter((row) => row.total > 0);

  if (measured.length === 0) {
    return (
      <EmptyState
        title="אין עדיין מה להשוות"
        message="דרג תשובות ידנית והפעל judge — ההסכמה נמדדת רק על שורות שיש להן שתי פסיקות."
      />
    );
  }

  return (
    <>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>קריטריון</th>
              <th>אחוז הסכמה</th>
              <th className="num">תשובות שנמדדו</th>
            </tr>
          </thead>
          <tbody>
            {measured.map((row) => (
              <tr key={row.criterion}>
                <td>{row.criterion}</td>
                <td>
                  <div className="meter">
                    <div className="meter-track">
                      <div className="meter-fill" style={{ width: `${row.agreement_pct}%` }} />
                    </div>
                    <span className="meter-value">{Math.round(row.agreement_pct)}%</span>
                  </div>
                </td>
                <td className="num">{row.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 style={{ marginBlockStart: 'var(--space-5)' }}>אי-הסכמות</h3>
      {data.disagreements.length === 0 ? (
        <p className="muted">אין אי-הסכמות.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>שאלה</th>
                <th>קריטריון</th>
                <th>אנושי</th>
                <th>Judge</th>
                <th>נימוק ה-judge</th>
              </tr>
            </thead>
            <tbody>
              {data.disagreements.map((row, index) => (
                <tr key={`${row.llm_call_id}-${row.criterion}-${index}`}>
                  <td><div className="cell-clamp">{row.question_text}</div></td>
                  <td className="nowrap">{row.criterion}</td>
                  <td><Badge tone={row.human_verdict}>{row.human_verdict}</Badge></td>
                  <td><Badge tone={row.judge_verdict}>{row.judge_verdict}</Badge></td>
                  <td>{row.judge_explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
