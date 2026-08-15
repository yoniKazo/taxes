import { submitRating } from '../api/client.js';

const VERDICTS = ['good', 'ok', 'bad'];

function FinalScoreBadge({ score }) {
  if (!score) {
    return <span className="badge">—</span>;
  }
  return <span className={`badge ${score === 'pass' ? 'good' : 'bad'}`}>{score}</span>;
}

export default function ResultsTable({ run, criteria, onRatingChanged, judgeRan }) {
  if (!run) {
    return null;
  }

  const results = run.results || [];

  async function handleRate(llmCallId, criterionName, verdict) {
    try {
      await submitRating(llmCallId, {
        rater: 'human',
        scores: { [criterionName]: verdict },
      });
      onRatingChanged?.();
    } catch (err) {
      window.alert(`שגיאה בשמירת ניקוד: ${err.message}`);
    }
  }

  return (
    <div className="card results-table">
      <h2>תוצאות הריצה</h2>
      <div style={{ overflowX: 'auto' }}>
        <table>
          <thead>
            <tr>
              <th>שאלה</th>
              <th>תשובה</th>
              <th>latency / tokens</th>
              {criteria.map((criterion) => (
                <th key={criterion.name}>{criterion.name}</th>
              ))}
              <th>ניקוד אנושי</th>
              {(judgeRan || results.some((r) => r.judge_final_score)) && <th>Judge</th>}
            </tr>
          </thead>
          <tbody>
            {results.map((result) => (
              <tr key={result.llm_call_id}>
                <td>{result.question_text}</td>
                <td>{result.error ? <span className="explanation-error">{result.error}</span> : result.response}</td>
                <td>
                  {result.latency_ms ? `${Math.round(result.latency_ms)}ms` : '—'}
                  <br />
                  {result.input_tokens ?? '—'}/{result.output_tokens ?? '—'}
                </td>
                {criteria.map((criterion) => {
                  const selected = result.human_ratings?.[criterion.name];
                  return (
                    <td key={criterion.name}>
                      <div className="rating-buttons">
                        {VERDICTS.map((verdict) => (
                          <button
                            key={verdict}
                            type="button"
                            className={selected === verdict ? `selected ${verdict}` : ''}
                            onClick={() => handleRate(result.llm_call_id, criterion.name, verdict)}
                          >
                            {verdict}
                          </button>
                        ))}
                      </div>
                    </td>
                  );
                })}
                <td>
                  <FinalScoreBadge score={result.human_final_score} />
                </td>
                {(judgeRan || results.some((r) => r.judge_final_score)) && (
                  <td>
                    {result.judge_final_score ? (
                      <details>
                        <summary>
                          <FinalScoreBadge score={result.judge_final_score} />
                        </summary>
                        <ul>
                          {criteria.map((criterion) => {
                            const judgeRating = result.judge_ratings?.[criterion.name];
                            if (!judgeRating) {
                              return null;
                            }
                            return (
                              <li key={criterion.name}>
                                <strong>{criterion.name}</strong>: {judgeRating.verdict} —{' '}
                                {judgeRating.explanation}
                              </li>
                            );
                          })}
                        </ul>
                      </details>
                    ) : (
                      '—'
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
