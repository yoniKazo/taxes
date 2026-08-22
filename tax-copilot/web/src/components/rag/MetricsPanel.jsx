import { GroupedBarChart } from '../ui/Chart.jsx';
import Stat from '../ui/Stat.jsx';

const SLICE_LABELS = { easy: 'קלות', hard: 'קשות', ALL: 'הכל' };

const ROWS = [
  ['rag_hit_at_k', 'hit-rate@K (מסמך)', 'rag'],
  ['rag_hit_at_k_any_doc', 'hit-rate@K (לפחות מסמך אחד)', 'rag'],
  ['rag_context_relevance', 'רלוונטיות הקטעים', 'rag'],
  ['rag_faithfulness', 'נאמנות למקור', 'rag'],
  ['rag_answer_relevance', 'רלוונטיות התשובה', 'both', 'baseline_answer_relevance'],
  ['rag_correctness', 'נכונות', 'both', 'baseline_correctness'],
];

function format(value) {
  return value == null ? '—' : Number(value).toFixed(3);
}

/**
 * Task 5's head-to-head, with the easy/hard split kept visible.
 *
 * The averaged column is the least informative one here: hit@k is 1.000 on the
 * easy slice and 0.750 on the hard one, and the ALL column (0.969) hides that
 * completely. The chart plots the three slices side by side for the same reason.
 */
export default function MetricsPanel({ data }) {
  const summary = data?.summary ?? [];
  const bySlice = Object.fromEntries(summary.map((row) => [row.slice, row]));

  const chartData = ['easy', 'hard', 'ALL'].map((slice) => ({
    name: SLICE_LABELS[slice],
    rag: bySlice[slice]?.rag_correctness ?? 0,
    baseline: bySlice[slice]?.baseline_correctness ?? 0,
    hit: bySlice[slice]?.rag_hit_at_k ?? 0,
  }));

  const all = bySlice.ALL ?? {};

  return (
    <>
      <div className="stat-row" style={{ marginBlockEnd: 'var(--space-4)' }}>
        <Stat
          label="נכונות RAG"
          value={format(all.rag_correctness)}
          caption={`מול ${format(all.baseline_correctness)} בבייסליין`}
          hero
        />
        <Stat label="hit-rate@K" value={format(all.rag_hit_at_k)} caption="ברמת מסמך" />
        <Stat
          label="סירובים שגויים"
          value={`${all.rag_false_refusals ?? 0} / ${all.baseline_false_refusals ?? 0}`}
          caption="RAG / בייסליין"
        />
        <Stat
          label="תשובות שגויות"
          value={`${all.rag_false_answers ?? 0} / ${all.baseline_false_answers ?? 0}`}
          caption="ענה כשהיה צריך לסרב"
        />
        <Stat
          label="ציטוטים מומצאים"
          value={data?.hallucinated_citation_rows ?? 0}
          caption="נתפסו בקוד, ללא קריאת LLM"
        />
      </div>

      <GroupedBarChart
        data={chartData}
        series={[
          { key: 'rag', label: 'נכונות — RAG' },
          { key: 'baseline', label: 'נכונות — בייסליין' },
          { key: 'hit', label: 'hit-rate@K' },
        ]}
      />

      <div className="panel-note warning" style={{ marginBlockStart: 'var(--space-4)' }}>
        <strong>הפרוסה הקשה מונה {data?.hard_slice_n ?? 6} שאלות בלבד.</strong> כל שאלה שווה
        ~16.7 נקודות אחוז — יותר מכפול מסף ה-3.3% שהמטלה מזהירה מפניו. כל דלתא בפרוסה הזו היא
        כיוון, לא הוכחה.
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>מדד</th>
              {summary.map((row) => (
                <th key={row.slice} className="num">
                  {SLICE_LABELS[row.slice] ?? row.slice} (n={row.n})
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map(([key, label, scope]) => (
              <tr key={key}>
                <td>
                  {label}
                  {scope === 'both' ? <span className="muted"> — RAG</span> : null}
                </td>
                {summary.map((row) => (
                  <td key={row.slice} className="num">{format(row[key])}</td>
                ))}
              </tr>
            ))}
            {ROWS.filter((row) => row[2] === 'both').map(([, label, , baselineKey]) => (
              <tr key={baselineKey}>
                <td>{label} <span className="muted">— בייסליין</span></td>
                {summary.map((row) => (
                  <td key={row.slice} className="num">{format(row[baselineKey])}</td>
                ))}
              </tr>
            ))}
            <tr>
              <td>זמן ממוצע (ms) — RAG / בייסליין</td>
              {summary.map((row) => (
                <td key={row.slice} className="num">
                  {Math.round(row.rag_latency_ms)} / {Math.round(row.baseline_latency_ms)}
                </td>
              ))}
            </tr>
            <tr>
              <td>טוקני קלט — RAG / בייסליין</td>
              {summary.map((row) => (
                <td key={row.slice} className="num">
                  {Math.round(row.rag_input_tokens)} / {Math.round(row.baseline_input_tokens)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <p className="muted" style={{ marginBlockStart: 'var(--space-3)' }}>
        רלוונטיות הקטעים ונאמנות למקור אינן מוגדרות לבייסליין — הוא לא אחזר דבר, ולכן אפס היה
        מטעה. ציונים ממופים good=1.0 / ok=0.5 / bad=0.
      </p>
    </>
  );
}
