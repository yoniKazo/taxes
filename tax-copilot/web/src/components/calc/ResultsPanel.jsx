import Stat from '../ui/Stat.jsx';

function formatCurrency(value) {
  if (value == null) return '—';
  return `₪${Number(value).toLocaleString('he-IL', { maximumFractionDigits: 0 })}`;
}

// The savings lines are the actionable ones -- they are what a refund claim is
// actually made of -- so they are broken out rather than buried in the list.
const SAVINGS = [
  ['pension_tax_savings', 'חיסכון מס — פנסיה'],
  ['keren_hishtalmut_tax_savings', 'חיסכון מס — קרן השתלמות'],
  ['donation_credit_annual', 'זיכוי תרומות'],
];

const BREAKDOWN = [
  ['combined_gross', 'ברוטו מצטבר'],
  ['tax_before_credit', 'מס לפני נקודות זיכוי'],
  ['tax_after_credit', 'מס אחרי נקודות זיכוי'],
  ['national_insurance', 'ביטוח לאומי'],
  ['health_tax', 'מס בריאות'],
];

export default function ResultsPanel({ result }) {
  if (!result) return null;

  const totalSavings = SAVINGS.reduce((sum, [key]) => sum + (result[key] ?? 0), 0);

  return (
    <>
      <div className="stat-row" style={{ marginBlockEnd: 'var(--space-4)' }}>
        {/* The net figure is the number the user came for. It used to be the
            tenth of ten identical table rows. */}
        <Stat label="נטו לשנה" value={formatCurrency(result.net)} hero />
        <Stat
          label="סה״כ חיסכון מס"
          value={formatCurrency(totalSavings)}
          caption="פנסיה + קרן השתלמות + תרומות"
        />
        <Stat label="מספר עבודות" value={result.job_count} />
      </div>

      <div className="table-scroll">
        <table>
          <tbody>
            {BREAKDOWN.map(([key, label]) => (
              <tr key={key}>
                <th scope="row">{label}</th>
                <td className="num">{formatCurrency(result[key])}</td>
              </tr>
            ))}
            {SAVINGS.map(([key, label]) => (
              <tr key={key}>
                <th scope="row">{label}</th>
                <td className="num" style={{ color: 'var(--success-fg)' }}>
                  {formatCurrency(result[key])}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
