import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { toast } from 'sonner';

import { submitRating } from '../../api/client.js';
import Badge, { VerdictBadge } from '../ui/Badge.jsx';
import DataTable from '../ui/DataTable.jsx';
import Drawer, { DrawerSection } from '../ui/Drawer.jsx';

const VERDICTS = ['good', 'ok', 'bad'];
const VERDICT_LABELS = { good: 'טוב', ok: 'בינוני', bad: 'גרוע' };

function FinalScore({ score }) {
  if (!score) return <span className="muted">—</span>;
  return <Badge tone={score === 'pass' ? 'pass' : 'fail'}>{score === 'pass' ? 'עבר' : 'נכשל'}</Badge>;
}

export default function ResultsTable({ run, compareRun, criteria }) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState(null);

  const rate = useMutation({
    mutationFn: ({ llmCallId, criterion, verdict }) =>
      submitRating(llmCallId, { rater: 'human', scores: { [criterion]: verdict } }),

    // Optimistic: the button fills immediately instead of after two round trips.
    // Rating is the highest-frequency interaction on this page and every click
    // used to lag behind a refetch, which made fast rating feel broken.
    onMutate: async ({ llmCallId, criterion, verdict }) => {
      const key = ['test-run', run.id];
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData(key);
      queryClient.setQueryData(key, (current) =>
        current && {
          ...current,
          results: current.results.map((result) =>
            result.llm_call_id === llmCallId
              ? { ...result, human_ratings: { ...result.human_ratings, [criterion]: verdict } }
              : result,
          ),
        },
      );
      return { previous, key };
    },
    onError: (error, _variables, context) => {
      if (context) queryClient.setQueryData(context.key, context.previous);
      toast.error(error.message);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['test-run', run.id] });
      queryClient.invalidateQueries({ queryKey: ['test-runs'] });
    },
  });

  const compareById = useMemo(() => {
    if (!compareRun) return null;
    return new Map(compareRun.results.map((result) => [result.question_text, result]));
  }, [compareRun]);

  if (!run) return null;

  const columns = [
    {
      key: 'question_text',
      label: 'שאלה',
      render: (row) => <div className="cell-clamp">{row.question_text}</div>,
    },
    {
      key: 'response',
      label: 'תשובה',
      render: (row) =>
        row.error ? (
          <Badge tone="bad" title={row.error}>שגיאה</Badge>
        ) : (
          // Clamped, with the full text one click away in the drawer -- untruncated
          // answers in a cell made row heights wildly uneven.
          <div className="cell-clamp">{row.response}</div>
        ),
    },
    ...(compareById
      ? [{
          key: 'compare',
          label: `ריצה #${compareRun.id}`,
          sortable: false,
          render: (row) => {
            const other = compareById.get(row.question_text);
            return other ? <div className="cell-clamp">{other.response}</div> : <span className="muted">—</span>;
          },
        }]
      : []),
    {
      key: 'latency_ms',
      label: 'זמן / טוקנים',
      numeric: true,
      render: (row) => (
        <span className="nowrap">
          {row.latency_ms ? `${Math.round(row.latency_ms)}ms` : '—'}
          <br />
          <span className="muted">{row.input_tokens ?? '—'}/{row.output_tokens ?? '—'}</span>
        </span>
      ),
    },
    ...criteria.map((criterion) => ({
      key: criterion.name,
      label: criterion.name,
      sortable: false,
      render: (row) => (
        <div className="rating-buttons" onClick={(event) => event.stopPropagation()}>
          {VERDICTS.map((verdict) => (
            <button
              key={verdict}
              type="button"
              className={row.human_ratings[criterion.name] === verdict ? `selected ${verdict}` : ''}
              onClick={() =>
                rate.mutate({ llmCallId: row.llm_call_id, criterion: criterion.name, verdict })
              }
            >
              {VERDICT_LABELS[verdict]}
            </button>
          ))}
        </div>
      ),
    })),
    {
      key: 'human_final_score',
      label: 'ניקוד אנושי',
      render: (row) => <FinalScore score={row.human_final_score} />,
    },
    {
      key: 'judge_final_score',
      label: 'Judge',
      render: (row) => <FinalScore score={row.judge_final_score} />,
    },
  ];

  return (
    <>
      <DataTable
        columns={columns}
        rows={run.results}
        rowKey={(row) => row.llm_call_id}
        onRowClick={setSelected}
        selectedKey={selected?.llm_call_id}
        searchable
        searchFields={['question_text', 'response']}
        emptyMessage="לריצה הזו אין תוצאות."
      />

      <Drawer
        open={Boolean(selected)}
        title={selected ? `תשובה #${selected.llm_call_id}` : ''}
        onClose={() => setSelected(null)}
      >
        {selected ? (
          <>
            <DrawerSection title="שאלה">
              <p>{selected.question_text}</p>
            </DrawerSection>

            <DrawerSection title="תשובה">
              {selected.error ? (
                <p style={{ color: 'var(--danger-fg)' }}>{selected.error}</p>
              ) : (
                <p style={{ whiteSpace: 'pre-wrap' }}>{selected.response}</p>
              )}
            </DrawerSection>

            {compareById?.get(selected.question_text) ? (
              <DrawerSection title={`אותה שאלה בריצה #${compareRun.id}`}>
                <p style={{ whiteSpace: 'pre-wrap' }}>
                  {compareById.get(selected.question_text).response}
                </p>
              </DrawerSection>
            ) : null}

            {Object.keys(selected.judge_ratings ?? {}).length ? (
              <DrawerSection title="נימוקי ה-judge">
                <table>
                  <tbody>
                    {Object.entries(selected.judge_ratings).map(([criterion, value]) => (
                      <tr key={criterion}>
                        <td className="nowrap">{criterion}</td>
                        <td><VerdictBadge verdict={value.verdict} /></td>
                        <td>{value.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </DrawerSection>
            ) : null}
          </>
        ) : null}
      </Drawer>
    </>
  );
}
