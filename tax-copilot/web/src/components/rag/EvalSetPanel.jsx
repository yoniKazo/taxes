import { Check, Play, X } from 'lucide-react';
import { useState } from 'react';

import Badge from '../ui/Badge.jsx';
import DataTable from '../ui/DataTable.jsx';

const CATEGORY_LABELS = {
  'multi-hop': 'רב-שלבית',
  unanswerable: 'ללא מענה',
  negation: 'שלילה',
  identifier: 'מזהה מדויק',
  synthetic: 'סינתטית',
};

/**
 * Task 2: the eval set, plus its coverage gates rendered as measured state.
 *
 * The assignment requires 25-40 questions, at least 6 hand-written hard ones, and
 * specific counts per hard category. Prose can claim that; this counts it, so a
 * question edited out of the CSV shows up here as a failed gate.
 */
export default function EvalSetPanel({ data, onUseQuestion }) {
  const [difficulty, setDifficulty] = useState('all');
  const questions = (data?.questions ?? []).filter(
    (row) => difficulty === 'all' || row.difficulty === difficulty,
  );

  const columns = [
    { key: 'id', label: '#', numeric: true, width: 48 },
    { key: 'question', label: 'שאלה', render: (row) => <div className="cell-clamp">{row.question}</div> },
    {
      key: 'category',
      label: 'קטגוריה',
      render: (row) => (
        <Badge tone={row.category === 'synthetic' ? 'neutral' : 'info'}>
          {CATEGORY_LABELS[row.category] ?? row.category}
        </Badge>
      ),
    },
    {
      key: 'difficulty',
      label: 'קושי',
      render: (row) => (
        <Badge tone={row.difficulty === 'hard' ? 'warning' : 'neutral'}>
          {row.difficulty === 'hard' ? 'קשה' : 'קלה'}
        </Badge>
      ),
    },
    {
      key: 'answerable',
      label: 'ניתנת למענה',
      render: (row) =>
        row.answerable ? <Check size={15} color="var(--success-fg)" /> : <X size={15} color="var(--danger-fg)" />,
    },
    { key: 'evidence_doc', label: 'מסמך הראיה', render: (row) => <span className="muted">{row.evidence_doc || '—'}</span> },
    {
      key: 'use',
      label: '',
      sortable: false,
      render: (row) => (
        <button
          type="button"
          className="ghost"
          title="טען את השאלה למגרש המשחקים"
          onClick={(event) => {
            event.stopPropagation();
            onUseQuestion(row);
          }}
        >
          <Play size={14} aria-hidden />
        </button>
      ),
    },
  ];

  return (
    <>
      <div className="row" style={{ marginBlockEnd: 'var(--space-4)', gap: 'var(--space-3)' }}>
        {(data?.coverage ?? []).map((item) => (
          <Badge key={item.category} tone={item.ok ? 'good' : 'bad'}>
            {item.ok ? <Check size={12} /> : <X size={12} />}
            {CATEGORY_LABELS[item.category] ?? item.category} {item.actual}/{item.required}
          </Badge>
        ))}
        <Badge tone={data?.size_ok ? 'good' : 'bad'}>
          {data?.size_ok ? <Check size={12} /> : <X size={12} />} היקף {data?.n} (נדרש 25–40)
        </Badge>
        <Badge tone={data?.hard_ok ? 'good' : 'bad'}>
          {data?.hard_ok ? <Check size={12} /> : <X size={12} />} קשות {data?.n_hard} (נדרש 6+)
        </Badge>
      </div>

      <DataTable
        columns={columns}
        rows={questions}
        searchable
        searchPlaceholder="חיפוש בשאלות…"
        searchFields={['question', 'reference_answer', 'evidence_doc']}
        initialSort={{ key: 'id', direction: 'asc' }}
        maxHeight={520}
        toolbar={
          <div className="pill-group">
            {[
              ['all', 'הכל'],
              ['easy', 'קלות'],
              ['hard', 'קשות'],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={difficulty === value ? 'active' : ''}
                onClick={() => setDifficulty(value)}
              >
                {label}
              </button>
            ))}
          </div>
        }
      />
    </>
  );
}
