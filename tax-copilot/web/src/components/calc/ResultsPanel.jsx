import Stat from '../ui/Stat.jsx';

function formatCurrency(value) {
  if (value == null) return '—';
  return `₪${Number(value).toLocaleString('he-IL', { maximumFractionDigits: 0 })}`;
}

// The savings lines are the actionable ones -- they are what a refund claim is
// actually made of -- so they are broken out rather than buried in the list.
// כל שורה כאן מוצגת גם חודשי וגם שנתי -- donation_credit_annual הוא שנתי מטבעו
// ואין לו תאום חודשי (ראו tax_notes.md §7), כך שהעמודה החודשית שלו ריקה.
const SAVINGS = [
  ['pension_tax_savings', 'pension_tax_savings_annual', 'חיסכון מס — פנסיה'],
  ['keren_hishtalmut_tax_savings', 'keren_hishtalmut_tax_savings_annual', 'חיסכון מס — קרן השתלמות'],
  [null, 'donation_credit_annual', 'זיכוי תרומות'],
];

const BREAKDOWN = [
  ['combined_gross', 'combined_gross_annual', 'ברוטו מצטבר'],
  ['tax_before_credit', 'tax_before_credit_annual', 'מס לפני נקודות זיכוי'],
  ['tax_after_credit', 'tax_after_credit_annual', 'מס אחרי נקודות זיכוי'],
  ['national_insurance', 'national_insurance_annual', 'ביטוח לאומי'],
  ['health_tax', 'health_tax_annual', 'מס בריאות'],
];

export default function ResultsPanel({ result }) {
  if (!result) return null;

  const totalSavingsAnnual = SAVINGS.reduce(
    (sum, [, annualKey]) => sum + (result[annualKey] ?? 0),
    0
  );

  return (
    <>
      <div className="stat-row" style={{ marginBlockEnd: 'var(--space-4)' }}>
        {/* הנטו הוא המספר שהמשתמש הגיע בשבילו -- מוצג בשתי היחידות כדי לא לחזור על
            הבאג הקודם, שבו תויג נטו חודשי בפועל בתור "נטו לשנה". */}
        <Stat label="נטו לשנה" value={formatCurrency(result.net_annual)} hero />
        <Stat label="נטו לחודש" value={formatCurrency(result.net)} hero />
        <Stat
          label="סה״כ חיסכון מס לשנה"
          value={formatCurrency(totalSavingsAnnual)}
          caption="פנסיה + קרן השתלמות + תרומות"
        />
        <Stat label="מספר עבודות" value={result.job_count} />
      </div>

      <div className="stat-row" style={{ marginBlockEnd: 'var(--space-4)' }}>
        <Stat
          label="נקודות זיכוי"
          value={result.total_credit_points}
          caption={`מתוכן ${result.estimated_credit_points} מוערכות מהעובדות שמולאו`}
        />
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col"></th>
              <th scope="col">לחודש</th>
              <th scope="col">לשנה</th>
            </tr>
          </thead>
          <tbody>
            {BREAKDOWN.map(([monthlyKey, annualKey, label]) => (
              <tr key={annualKey}>
                <th scope="row">{label}</th>
                <td className="num">{formatCurrency(result[monthlyKey])}</td>
                <td className="num">{formatCurrency(result[annualKey])}</td>
              </tr>
            ))}
            {SAVINGS.map(([monthlyKey, annualKey, label]) => (
              <tr key={annualKey}>
                <th scope="row">{label}</th>
                <td className="num" style={{ color: 'var(--success-fg)' }}>
                  {monthlyKey ? formatCurrency(result[monthlyKey]) : '—'}
                </td>
                <td className="num" style={{ color: 'var(--success-fg)' }}>
                  {formatCurrency(result[annualKey])}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
