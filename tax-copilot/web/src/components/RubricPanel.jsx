import { useEffect, useState } from 'react';
import { updateRubric } from '../api/client.js';

export default function RubricPanel({ rubric, loading, error, onSaved }) {
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  useEffect(() => {
    if (rubric) {
      setDraft({
        name: rubric.name,
        pass_bar_min_good: rubric.pass_bar_min_good,
        pass_bar_max_bad: rubric.pass_bar_max_bad,
        criteria: rubric.criteria.map((criterion) => ({ ...criterion })),
      });
    }
  }, [rubric]);

  function updateCriterion(index, field, value) {
    setDraft((prev) => {
      const criteria = prev.criteria.slice();
      criteria[index] = { ...criteria[index], [field]: value };
      return { ...prev, criteria };
    });
  }

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    try {
      await updateRubric(draft);
      onSaved?.();
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="card">
        <h2>רוברייק</h2>
        <p>טוען...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h2>רוברייק</h2>
        <p className="explanation-error">שגיאה בטעינת הרוברייק: {error}</p>
      </div>
    );
  }

  if (!draft) {
    return null;
  }

  return (
    <div className="card rubric-panel">
      <h2>רוברייק פעילה</h2>
      {saveError && <p className="explanation-error">שמירה נכשלה: {saveError}</p>}

      <div className="field-grid">
        <div>
          <label htmlFor="pass_bar_min_good">מינימום good ל-pass</label>
          <input
            id="pass_bar_min_good"
            type="number"
            min="0"
            value={draft.pass_bar_min_good}
            onChange={(event) =>
              setDraft((prev) => ({ ...prev, pass_bar_min_good: Number(event.target.value) }))
            }
          />
        </div>
        <div>
          <label htmlFor="pass_bar_max_bad">מקסימום bad ל-pass</label>
          <input
            id="pass_bar_max_bad"
            type="number"
            min="0"
            value={draft.pass_bar_max_bad}
            onChange={(event) =>
              setDraft((prev) => ({ ...prev, pass_bar_max_bad: Number(event.target.value) }))
            }
          />
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th>קריטריון</th>
            <th>הגדרת good</th>
            <th>הגדרת ok</th>
            <th>הגדרת bad</th>
            <th>קריטריון בטיחות (fails_unless_good)</th>
            <th>דוחה אוטומטית אם bad (fails_if_bad)</th>
          </tr>
        </thead>
        <tbody>
          {draft.criteria.map((criterion, index) => (
            <tr key={criterion.name}>
              <td>
                {criterion.name}
                {criterion.is_programmatic && <span className="badge ok"> מחושב אוטומטית</span>}
              </td>
              <td>
                <textarea
                  rows={2}
                  value={criterion.good_def}
                  onChange={(event) => updateCriterion(index, 'good_def', event.target.value)}
                  disabled={criterion.is_programmatic}
                />
              </td>
              <td>
                <textarea
                  rows={2}
                  value={criterion.ok_def}
                  onChange={(event) => updateCriterion(index, 'ok_def', event.target.value)}
                  disabled={criterion.is_programmatic}
                />
              </td>
              <td>
                <textarea
                  rows={2}
                  value={criterion.bad_def}
                  onChange={(event) => updateCriterion(index, 'bad_def', event.target.value)}
                  disabled={criterion.is_programmatic}
                />
              </td>
              <td>
                <input
                  type="checkbox"
                  checked={Boolean(criterion.fails_unless_good)}
                  onChange={(event) =>
                    updateCriterion(index, 'fails_unless_good', event.target.checked)
                  }
                />
              </td>
              <td>
                <input
                  type="checkbox"
                  checked={Boolean(criterion.fails_if_bad)}
                  onChange={(event) => updateCriterion(index, 'fails_if_bad', event.target.checked)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="form-actions">
        <button type="button" className="primary" onClick={handleSave} disabled={saving}>
          {saving ? 'שומר...' : 'שמור גרסה חדשה'}
        </button>
      </div>
    </div>
  );
}
