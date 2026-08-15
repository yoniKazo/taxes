function formatCurrency(value) {
  if (value === null || value === undefined) {
    return '—';
  }
  return `₪${Number(value).toLocaleString('he-IL', { maximumFractionDigits: 0 })}`;
}

const ROWS = [
  { key: 'combined_gross', label: 'סך ברוטו משולב' },
  { key: 'job_count', label: 'מספר עבודות', raw: true },
  { key: 'tax_before_credit', label: 'מס לפני זיכויים' },
  { key: 'tax_after_credit', label: 'מס אחרי זיכויים' },
  { key: 'national_insurance', label: 'ביטוח לאומי' },
  { key: 'health_tax', label: 'דמי בריאות' },
  { key: 'pension_tax_savings', label: 'חיסכון מס — פנסיה' },
  { key: 'keren_hishtalmut_tax_savings', label: 'חיסכון מס — קרן השתלמות' },
  { key: 'donation_credit_annual', label: 'זיכוי מס — תרומות' },
  { key: 'net', label: 'נטו' },
];

export default function ResultsPanel({ result }) {
  if (!result) {
    return null;
  }

  return (
    <div className="card results-panel">
      <h2>תוצאות</h2>
      <table>
        <tbody>
          {ROWS.map((row) => (
            <tr key={row.key}>
              <th scope="row">{row.label}</th>
              <td>{row.raw ? result[row.key] : formatCurrency(result[row.key])}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
