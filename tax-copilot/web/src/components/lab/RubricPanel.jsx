import { useMutation, useQueryClient } from '@tanstack/react-query';
import { RotateCcw, Save } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import { updateRubric } from '../../api/client.js';
import Badge from '../ui/Badge.jsx';

function cloneRubric(rubric) {
  return {
    name: rubric.name,
    pass_bar_min_good: rubric.pass_bar_min_good,
    pass_bar_max_bad: rubric.pass_bar_max_bad,
    criteria: rubric.criteria.map((criterion) => ({ ...criterion })),
  };
}

export default function RubricPanel({ rubric }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState(null);

  // Seed the draft once per rubric VERSION, not on every parent refetch. The old
  // effect keyed on the rubric object, so any background refresh silently wiped
  // whatever the user was mid-way through typing.
  useEffect(() => {
    if (rubric) setDraft(cloneRubric(rubric));
  }, [rubric?.name, rubric?.pass_bar_min_good, rubric?.pass_bar_max_bad]); // eslint-disable-line react-hooks/exhaustive-deps

  const dirty = useMemo(
    () => Boolean(rubric && draft) && JSON.stringify(cloneRubric(rubric)) !== JSON.stringify(draft),
    [rubric, draft],
  );

  const save = useMutation({
    mutationFn: () => updateRubric(draft),
    onSuccess: () => {
      toast.success('נשמרה גרסה חדשה של הרוברייק.');
      queryClient.invalidateQueries({ queryKey: ['rubric'] });
    },
    onError: (error) => toast.error(error.message),
  });

  if (!draft) return null;

  const updateCriterion = (index, field, value) =>
    setDraft((current) => ({
      ...current,
      criteria: current.criteria.map((criterion, i) =>
        i === index ? { ...criterion, [field]: value } : criterion,
      ),
    }));

  return (
    <>
      <div className="field-grid" style={{ marginBlockEnd: 'var(--space-4)' }}>
        <div>
          <label htmlFor="bar-good">מינימום ״טוב״ למעבר</label>
          <input
            id="bar-good"
            type="number"
            min={0}
            value={draft.pass_bar_min_good}
            onChange={(event) =>
              setDraft({ ...draft, pass_bar_min_good: Number(event.target.value) })
            }
          />
        </div>
        <div>
          <label htmlFor="bar-bad">מקסימום ״גרוע״ למעבר</label>
          <input
            id="bar-bad"
            type="number"
            min={0}
            value={draft.pass_bar_max_bad}
            onChange={(event) =>
              setDraft({ ...draft, pass_bar_max_bad: Number(event.target.value) })
            }
          />
        </div>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>קריטריון</th>
              <th>טוב</th>
              <th>בינוני</th>
              <th>גרוע</th>
              <th>חובה ״טוב״</th>
              <th>״גרוע״ פוסל</th>
            </tr>
          </thead>
          <tbody>
            {draft.criteria.map((criterion, index) => (
              <tr key={criterion.name}>
                <td className="nowrap">
                  {criterion.name}
                  {criterion.is_programmatic ? (
                    <>
                      <br />
                      <Badge tone="info">מחושב בקוד</Badge>
                    </>
                  ) : null}
                </td>
                {['good_def', 'ok_def', 'bad_def'].map((field) => (
                  <td key={field} style={{ minWidth: 200 }}>
                    <textarea
                      rows={2}
                      value={criterion[field]}
                      disabled={criterion.is_programmatic}
                      onChange={(event) => updateCriterion(index, field, event.target.value)}
                      aria-label={`${criterion.name} — ${field}`}
                    />
                  </td>
                ))}
                <td>
                  <input
                    type="checkbox"
                    checked={criterion.fails_unless_good}
                    onChange={(event) =>
                      updateCriterion(index, 'fails_unless_good', event.target.checked)
                    }
                    aria-label={`${criterion.name} — חובה טוב`}
                  />
                </td>
                <td>
                  <input
                    type="checkbox"
                    checked={criterion.fails_if_bad}
                    onChange={(event) => updateCriterion(index, 'fails_if_bad', event.target.checked)}
                    aria-label={`${criterion.name} — גרוע פוסל`}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="row" style={{ marginBlockStart: 'var(--space-4)' }}>
        <button type="button" className="primary" onClick={() => save.mutate()} disabled={!dirty || save.isPending}>
          <Save size={15} aria-hidden />
          {save.isPending ? 'שומר…' : 'שמור גרסה חדשה'}
        </button>
        {dirty ? (
          <>
            <button type="button" className="ghost" onClick={() => setDraft(cloneRubric(rubric))}>
              <RotateCcw size={14} aria-hidden />
              בטל שינויים
            </button>
            <Badge tone="warning">יש שינויים שלא נשמרו</Badge>
          </>
        ) : null}
      </div>

      <p className="muted" style={{ marginBlockStart: 'var(--space-3)' }}>
        שמירה יוצרת <strong>גרסה חדשה</strong> ולא עורכת את הקיימת — ריצות ישנות ממשיכות
        להצביע על הרוברייק שבאמת הייתה בשימוש בזמנן.
      </p>
    </>
  );
}
