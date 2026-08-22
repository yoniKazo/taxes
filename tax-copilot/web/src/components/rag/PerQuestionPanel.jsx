import { Check, X } from 'lucide-react';
import { useState } from 'react';

import Badge, { VerdictBadge } from '../ui/Badge.jsx';
import DataTable from '../ui/DataTable.jsx';
import Drawer, { DrawerSection } from '../ui/Drawer.jsx';

const JUDGES = [
  ['rag_context_relevance', 'רלוונטיות הקטעים'],
  ['rag_faithfulness', 'נאמנות למקור'],
  ['rag_answer_relevance', 'רלוונטיות התשובה'],
  ['rag_correctness', 'נכונות'],
];

/**
 * Every judged row, with the retrieved chunks behind it.
 *
 * The drawer exists because the assignment's own instruction is to look at the
 * chunks before diagnosing anything -- a verdict column on its own cannot tell
 * you whether the right paragraph was missing or present-but-misused.
 */
export default function PerQuestionPanel({ data }) {
  const [selected, setSelected] = useState(null);

  const columns = [
    { key: 'id', label: '#', numeric: true, width: 48 },
    { key: 'question', label: 'שאלה', render: (row) => <div className="cell-clamp">{row.question}</div> },
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
      key: 'hit_at_k',
      label: 'hit@k',
      render: (row) =>
        row.hit_at_k == null ? (
          <span className="muted" title="שאלה ללא מענה — אחזור לא נמדד">—</span>
        ) : row.hit_at_k ? (
          <Check size={15} color="var(--success-fg)" />
        ) : (
          <X size={15} color="var(--danger-fg)" />
        ),
    },
    ...JUDGES.map(([key, label]) => ({
      key,
      label,
      render: (row) => <VerdictBadge verdict={row[key]} title={row[`${key}_explanation`]} />,
    })),
  ];

  return (
    <>
      <DataTable
        columns={columns}
        rows={data?.rows ?? []}
        searchable
        searchFields={['question', 'rag_answer', 'reference_answer']}
        initialSort={{ key: 'id', direction: 'asc' }}
        onRowClick={setSelected}
        selectedKey={selected?.id}
        maxHeight={560}
      />

      <Drawer
        open={Boolean(selected)}
        title={selected ? `שאלה #${selected.id}` : ''}
        onClose={() => setSelected(null)}
      >
        {selected ? (
          <>
            <DrawerSection title="שאלה">
              <p>{selected.question}</p>
              <div className="row">
                <Badge tone="info">{selected.category}</Badge>
                <Badge tone={selected.difficulty === 'hard' ? 'warning' : 'neutral'}>
                  {selected.difficulty === 'hard' ? 'קשה' : 'קלה'}
                </Badge>
                <Badge tone={selected.answerable ? 'good' : 'bad'}>
                  {selected.answerable ? 'ניתנת למענה' : 'ללא מענה בקורפוס'}
                </Badge>
              </div>
            </DrawerSection>

            <DrawerSection title="תשובת ייחוס">
              <p className="muted">{selected.reference_answer || '—'}</p>
            </DrawerSection>

            <DrawerSection title="בייסליין (ללא RAG)">
              <p>{selected.baseline_answer}</p>
              <Badge tone={selected.baseline_classification}>{selected.baseline_classification}</Badge>
            </DrawerSection>

            <DrawerSection title="תשובת RAG">
              <p>{selected.rag_answer}</p>
              <div className="row">
                <Badge tone={selected.rag_answered ? 'good' : 'neutral'}>
                  {selected.rag_answered ? 'ענה' : 'סירב'}
                </Badge>
                <span className="muted">
                  {Math.round(selected.latency_ms)} ms · {selected.input_tokens} טוקני קלט
                </span>
              </div>
            </DrawerSection>

            <DrawerSection title="פסיקות השופטים">
              <table>
                <tbody>
                  {JUDGES.map(([key, label]) => (
                    <tr key={key}>
                      <td className="nowrap">{label}</td>
                      <td><VerdictBadge verdict={selected[key]} /></td>
                      <td>{selected[`${key}_explanation`]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </DrawerSection>

            <DrawerSection title={`הקטעים שאוחזרו בפועל (${selected.retrieved_docs?.length ?? 0})`}>
              {(selected.retrieved_texts ?? []).map((text, index) => (
                <article key={index} className="chunk-card" style={{ marginBlockEnd: 'var(--space-3)' }}>
                  <header className="chunk-head">
                    <span className="chunk-rank">{index + 1}</span>
                    <div className="grow">
                      <div className="chunk-doc">{selected.retrieved_docs?.[index]}</div>
                      <div className="chunk-where">{selected.retrieved_locations?.[index]}</div>
                    </div>
                  </header>
                  <div className="chunk-text">{text}</div>
                </article>
              ))}
            </DrawerSection>
          </>
        ) : null}
      </Drawer>
    </>
  );
}
