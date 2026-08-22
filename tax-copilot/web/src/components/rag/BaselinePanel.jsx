import Badge from '../ui/Badge.jsx';
import DataTable from '../ui/DataTable.jsx';
import Stat from '../ui/Stat.jsx';

const BUCKETS = [
  ['refused', 'סירב', 'neutral'],
  ['correct', 'ענה נכון', 'good'],
  ['partial', 'חלקי', 'ok'],
  ['hallucinated', 'הזיה', 'bad'],
];

/** Task 1: how the model behaves with no retrieval at all. */
export default function BaselinePanel({ data }) {
  const buckets = data?.buckets ?? {};
  const total = data?.n ?? 0;

  const columns = [
    { key: 'id', label: '#', numeric: true, width: 48 },
    { key: 'question', label: 'שאלה', render: (row) => <div className="cell-clamp">{row.question}</div> },
    {
      key: 'baseline_classification',
      label: 'סיווג',
      render: (row) => {
        const bucket = BUCKETS.find(([key]) => key === row.baseline_classification);
        return <Badge tone={bucket?.[2] ?? 'neutral'}>{bucket?.[1] ?? row.baseline_classification}</Badge>;
      },
    },
    {
      key: 'baseline_answer',
      label: 'תשובת הבייסליין',
      render: (row) => <div className="cell-clamp">{row.baseline_answer}</div>,
    },
    { key: 'baseline_latency_ms', label: 'זמן (ms)', numeric: true, render: (row) => Math.round(row.baseline_latency_ms) },
  ];

  return (
    <>
      <div className="stat-row" style={{ marginBlockEnd: 'var(--space-4)' }}>
        {BUCKETS.map(([key, label, tone]) => (
          <Stat
            key={key}
            label={label}
            value={buckets[key] ?? 0}
            caption={total ? `${Math.round(((buckets[key] ?? 0) / total) * 100)}%` : undefined}
            tone={tone === 'neutral' ? undefined : tone === 'good' ? 'success' : tone === 'ok' ? 'warning' : 'danger'}
          />
        ))}
      </div>

      <div className="panel-note">
        <strong>למה יש דלי רביעי.</strong> המטלה מבקשת שלושה דליים, אבל מיפוי של כל verdict
        שאינו <code>good</code> ל״הזיה״ מנפח את שיעור ההזיות: <code>ok</code> פירושו תשובה נכונה
        בכיוון אך חסרה, לא תשובה בטוחה ושגויה. הסיווג מחושב מחדש מפסיקת ה-correctness שכבר
        הופקה ב-Task 5, ולכן עלה 0 קריאות נוספות — ו״חלקי״ מדווח בנפרד במקום להסתתר.
      </div>

      <DataTable
        columns={columns}
        rows={data?.rows ?? []}
        searchable
        searchFields={['question', 'baseline_answer']}
        initialSort={{ key: 'id', direction: 'asc' }}
        maxHeight={460}
      />
    </>
  );
}
