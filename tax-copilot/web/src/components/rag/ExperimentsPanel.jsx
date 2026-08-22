import Badge from '../ui/Badge.jsx';
import ProgressBar from '../ui/ProgressBar.jsx';

const STATUS = {
  complete: ['הושלם', 'complete'],
  partial: ['לא הושלם', 'partial'],
  missing: ['לא רץ', 'missing'],
};

/**
 * Task 6 phase B: the three pre-registered hypotheses and what came of them.
 *
 * Two of the three did not finish -- exp1 was judged for 6 of 34 rows before the
 * run hit the 500-calls-per-day cap, exp3 never ran. They are shown as
 * incomplete rather than as a mean over whatever rows exist: averaging 6 rows
 * beside a 34-row baseline would read as a result and is not one.
 */
export default function ExperimentsPanel({ data }) {
  const experiments = data?.experiments ?? [];

  return (
    <div className="stack">
      {experiments.map((experiment) => {
        const [label, tone] = STATUS[experiment.status] ?? STATUS.missing;
        return (
          <article key={experiment.name} className="chunk-card">
            <header className="chunk-head">
              <div className="grow">
                <div className="chunk-doc">{experiment.name}</div>
                <div className="chunk-where">{experiment.changed}</div>
              </div>
              <Badge tone={tone}>{label}</Badge>
            </header>

            <div style={{ padding: 'var(--space-3)' }}>
              <h4 className="drawer-section-title">השערה (נרשמה לפני ההרצה)</h4>
              <p className="muted" style={{ fontSize: 'var(--text-sm)' }}>{experiment.hypothesis}</p>

              {experiment.status === 'complete' && experiment.metrics ? (
                <div className="table-scroll" style={{ marginBlockStart: 'var(--space-3)' }}>
                  <table>
                    <tbody>
                      {Object.entries(experiment.metrics).map(([key, value]) => (
                        <tr key={key}>
                          <td>{key}</td>
                          <td className="num">
                            {typeof value === 'number' ? value.toFixed(3) : String(value)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ marginBlockStart: 'var(--space-3)' }}>
                  <ProgressBar
                    phase={
                      experiment.generation_complete
                        ? 'היצירה הושלמה; השיפוט נעצר'
                        : 'לא הורץ'
                    }
                    done={experiment.rows_judged}
                    total={experiment.rows_total}
                  />
                  <p className="muted" style={{ marginBlockStart: 'var(--space-2)', fontSize: 'var(--text-sm)' }}>
                    {experiment.rows_judged > 0
                      ? `שופטו ${experiment.rows_judged} מתוך ${experiment.rows_total} שורות לפני שההרצה נעצרה במכסה היומית (500 קריאות). ממוצע על ${experiment.rows_judged} שורות מול בייסליין של ${experiment.rows_total} אינו השוואה, ולכן לא מוצג מספר.`
                      : 'הניסוי לא הורץ. ניסוי שלא הורץ אינו מסקנה.'}
                  </p>
                </div>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}
