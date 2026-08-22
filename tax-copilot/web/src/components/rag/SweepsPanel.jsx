import { useState } from 'react';

import { GroupedBarChart } from '../ui/Chart.jsx';
import DataTable from '../ui/DataTable.jsx';

const AXIS_LABELS = {
  top_k: 'top-K',
  chunk_size: "גודל צ'אנק",
  embedding_model: 'מודל embedding',
  hybrid_bm25: 'hybrid BM25',
};

const BASELINE = {
  top_k: 'k=5',
  chunk_size: '1000/150',
  embedding_model: 'intfloat/multilingual-e5-small',
  hybrid_bm25: null,
};

/**
 * Task 6 phase A: twelve configurations swept against hit-rate for zero API calls.
 *
 * The chart and the table both ship, always. That is not redundancy -- the aqua
 * series sits below 3:1 against the light surface, and the table is the relief
 * that makes it readable.
 */
export default function SweepsPanel({ data, liveResult }) {
  const [axis, setAxis] = useState('top_k');
  const rows = (data?.rows ?? []).filter((row) => row.sweep === axis);

  const chartData = rows.map((row) => ({
    name: row.setting.replace('intfloat/', '').replace('BAAI/', ''),
    all: row.hit_at_k,
    easy: row.hit_at_k_easy,
    hard: row.hit_at_k_hard,
    isBaseline: row.setting === BASELINE[axis],
  }));

  // A config the user just measured lands on the same axes as the recorded
  // sweep, so "did my change help?" is one glance rather than a comparison
  // against a number in a different panel.
  if (liveResult && matchesAxis(axis, liveResult)) {
    chartData.push({
      name: `שלי (k=${liveResult.k})`,
      all: liveResult.hit_at_k,
      easy: liveResult.hit_at_k_easy,
      hard: liveResult.hit_at_k_hard,
      isLive: true,
    });
  }

  const columns = [
    { key: 'setting', label: 'הגדרה' },
    { key: 'hit_at_k', label: 'hit@k', numeric: true, render: (r) => r.hit_at_k.toFixed(3) },
    { key: 'hit_at_k_easy', label: 'קלות', numeric: true, render: (r) => r.hit_at_k_easy.toFixed(3) },
    { key: 'hit_at_k_hard', label: 'קשות', numeric: true, render: (r) => r.hit_at_k_hard.toFixed(3) },
    {
      key: 'n_chunks',
      label: "צ'אנקים",
      numeric: true,
      render: (r) => (r.n_chunks == null ? '—' : Math.round(r.n_chunks)),
    },
  ];

  return (
    <>
      <div className="pill-group" style={{ marginBlockEnd: 'var(--space-4)' }}>
        {(data?.axes ?? []).map((name) => (
          <button
            key={name}
            type="button"
            className={axis === name ? 'active' : ''}
            onClick={() => setAxis(name)}
          >
            {AXIS_LABELS[name] ?? name}
          </button>
        ))}
      </div>

      <GroupedBarChart
        data={chartData}
        series={[
          { key: 'all', label: 'hit@k — הכל' },
          { key: 'easy', label: 'קלות' },
          { key: 'hard', label: 'קשות' },
        ]}
      />

      <div style={{ marginBlockStart: 'var(--space-4)' }}>
        <DataTable columns={columns} rows={rows} rowKey={(row) => row.setting} />
      </div>

      <div className="panel-note" style={{ marginBlockStart: 'var(--space-4)' }}>
        {SWEEP_NOTES[axis]}
      </div>
    </>
  );
}

function matchesAxis(axis, result) {
  return axis === 'top_k' || (axis === 'hybrid_bm25' && result.retriever === 'hybrid');
}

const SWEEP_NOTES = {
  top_k: 'k=8 מעלה את הפרוסה הקשה מ-0.750 ל-1.000 בלי לפגוע בקלה. k=10 לא מוסיף — כל הרווח נמצא בין 5 ל-8.',
  chunk_size:
    "1000/150 מנצח לשני הכיוונים. 500/100 מעלה את הקשות ל-1.000 אבל מוריד את הקלות: צ'אנקים קטנים עוזרים ל-multi-hop (יותר מסמכים נכנסים ל-top-K) ופוגעים בשאלות שצריכות הקשר רציף.",
  embedding_model:
    'bge הוא מודל אנגלית-בלבד עם tokenizer אנגלי. על הקורפוס העברי הוא מאבד ~0.20 נקודות פיזור בין שאילתות — ההבחנה בין שאלות שונות מצטמצמת עד שהדירוג מאבד משמעות.',
  hybrid_bm25:
    'BM25 לא מנצח dense טהור באף משקל. dense=0.7 שקול לבייסליין; משקלים נמוכים עושים את אותה החלפה כמו צ׳אנקים קטנים — עולים בקשות, יורדים בקלות. ההשערה שנרשמה מראש הופרכה כאן.',
};
