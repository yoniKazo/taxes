import { Plus, Trash2 } from 'lucide-react';

/**
 * נקודות זיכוי מחושבות מעובדות, לא מוזנות כמספר.
 *
 * המשתמש/ת ממלא/ה עובדות (ילדים+גיל, הורה יחיד, אזור זכאי, שירות/עלייה/תואר) והשרת
 * מתרגם אותן לנקודות זיכוי לפי הטבלאות ב-data/tax_notes.md §2 -- אין ציפייה שהמשתמש/ת
 * ידע/תדע כמה נקודות מגיעות לו/ה מראש.
 */
export default function CreditPointsForm({ values, onChange, makeChild }) {
  const update = (field, value) => onChange({ ...values, [field]: value });
  const updateNested = (field, subField, value) =>
    onChange({ ...values, [field]: { ...values[field], [subField]: value } });

  const updateChild = (id, age) =>
    onChange({
      ...values,
      children: values.children.map((child) => (child.id === id ? { ...child, age } : child)),
    });

  return (
    <div className="stack">
      <div className="field-grid">
        <div>
          <label htmlFor="gender">מגדר</label>
          <select
            id="gender"
            value={values.gender}
            onChange={(event) => update('gender', event.target.value)}
          >
            <option value="male">זכר</option>
            <option value="female">נקבה</option>
          </select>
          <div className="field-hint">קובע נקודות זיכוי בסיס, וגם את עמודת ההורה בטבלת הילדים</div>
        </div>
      </div>

      <div>
        <label>ילדים</label>
        <div className="field-hint" style={{ marginBlockEnd: 'var(--space-2)' }}>
          גיל נכון לשנת המס הנוכחית -- כל גיל מתורגם אוטומטית למספר נקודות הזיכוי שלו
        </div>
        {values.children.map((child) => (
          <div
            key={child.id}
            className="row"
            style={{ marginBlockEnd: 'var(--space-2)', alignItems: 'center' }}
          >
            <input
              type="number"
              min="0"
              max="18"
              value={child.age}
              onChange={(event) => updateChild(child.id, event.target.value)}
              placeholder="גיל"
              aria-label="גיל הילד/ה"
              style={{ maxWidth: '6rem' }}
            />
            <button
              type="button"
              className="ghost"
              onClick={() =>
                onChange({
                  ...values,
                  children: values.children.filter((item) => item.id !== child.id),
                })
              }
            >
              <Trash2 size={14} aria-hidden />
              הסר
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => onChange({ ...values, children: [...values.children, makeChild()] })}
        >
          <Plus size={15} aria-hidden />
          הוסף ילד/ה
        </button>
      </div>

      <div className="field-grid">
        <label className="row" style={{ alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={values.is_single_parent}
            onChange={(event) => update('is_single_parent', event.target.checked)}
          />
          הורה יחיד
        </label>
        <label className="row" style={{ alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={values.lives_in_eligible_zone}
            onChange={(event) => update('lives_in_eligible_zone', event.target.checked)}
          />
          מתגורר/ת באזור עדיפות לאומית / יישוב ספר
        </label>
      </div>

      <div>
        <label className="row" style={{ alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={values.discharged_service_enabled}
            onChange={(event) => update('discharged_service_enabled', event.target.checked)}
          />
          חייל/ת משוחרר/ת או מסיים/ת שירות לאומי-אזרחי (עד 3 שנים מהשחרור)
        </label>
        {values.discharged_service_enabled ? (
          <div className="field-grid" style={{ marginBlockStart: 'var(--space-2)' }}>
            <div>
              <label htmlFor="service_type">סוג שירות</label>
              <select
                id="service_type"
                value={values.discharged_service.service_type}
                onChange={(event) =>
                  updateNested('discharged_service', 'service_type', event.target.value)
                }
              >
                <option value="military">צבאי</option>
                <option value="national">לאומי-אזרחי</option>
              </select>
            </div>
            <div>
              <label htmlFor="months_since_discharge">חודשים מאז השחרור</label>
              <input
                id="months_since_discharge"
                type="number"
                min="0"
                value={values.discharged_service.months_since_discharge}
                onChange={(event) =>
                  updateNested('discharged_service', 'months_since_discharge', event.target.value)
                }
              />
            </div>
            <div>
              <label htmlFor="service_length_months">אורך השירות (חודשים)</label>
              <input
                id="service_length_months"
                type="number"
                min="0"
                value={values.discharged_service.service_length_months}
                onChange={(event) =>
                  updateNested('discharged_service', 'service_length_months', event.target.value)
                }
              />
            </div>
          </div>
        ) : null}
      </div>

      <div>
        <label className="row" style={{ alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={values.new_immigrant_enabled}
            onChange={(event) => update('new_immigrant_enabled', event.target.checked)}
          />
          עולה חדש/ה או קטין/ה חוזר/ת (עד 4.5 שנים מהעלייה)
        </label>
        {values.new_immigrant_enabled ? (
          <div className="field-grid" style={{ marginBlockStart: 'var(--space-2)' }}>
            <div>
              <label htmlFor="months_since_aliyah">חודשים מאז העלייה</label>
              <input
                id="months_since_aliyah"
                type="number"
                min="0"
                value={values.new_immigrant.months_since_aliyah}
                onChange={(event) =>
                  updateNested('new_immigrant', 'months_since_aliyah', event.target.value)
                }
              />
              <div className="field-hint">
                טבלת המקור לשלב הזה אינה עמוד רשמי ייעודי של רשות המסים -- כדאי לאמת מול תיאום מס
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <div>
        <label className="row" style={{ alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={values.academic_degree_enabled}
            onChange={(event) => update('academic_degree_enabled', event.target.checked)}
          />
          סיימתי תואר אקדמי / תעודת הנדסאי בשנים האחרונות
        </label>
        {values.academic_degree_enabled ? (
          <div className="field-grid" style={{ marginBlockStart: 'var(--space-2)' }}>
            <div>
              <label htmlFor="graduation_year">שנת סיום הלימודים</label>
              <input
                id="graduation_year"
                type="number"
                min="2000"
                value={values.academic_degree.graduation_year}
                onChange={(event) =>
                  updateNested('academic_degree', 'graduation_year', event.target.value)
                }
              />
            </div>
            <div>
              <label htmlFor="program_years">אורך הלימודים (שנים)</label>
              <input
                id="program_years"
                type="number"
                min="1"
                value={values.academic_degree.program_years}
                onChange={(event) =>
                  updateNested('academic_degree', 'program_years', event.target.value)
                }
              />
            </div>
          </div>
        ) : null}
      </div>

      <div className="field-grid">
        <div>
          <label htmlFor="extra_credit_points">נקודות זיכוי נוספות ידניות</label>
          <input
            id="extra_credit_points"
            type="number"
            min="0"
            step="0.25"
            value={values.extra_credit_points}
            onChange={(event) => update('extra_credit_points', event.target.value)}
          />
          <div className="field-hint">למקרים שלא מכוסים למעלה -- למשל לפי אישור מרואה חשבון</div>
        </div>
      </div>
    </div>
  );
}
