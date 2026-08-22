/**
 * Every numeric field carries its unit.
 *
 * Pension is a percentage, keren hishtalmut is shekels per month, and donations
 * are shekels per year -- three different units in adjacent boxes. That fact
 * previously lived only in a comment inside buildPayload(), where the person
 * filling the form could not see it.
 */
export default function SharedFieldsForm({ values, onChange }) {
  const update = (field, value) => onChange({ ...values, [field]: value });

  return (
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
        <div className="field-hint">נשים מקבלות חצי נקודת זיכוי נוספת</div>
      </div>

      <div>
        <label htmlFor="extra_credit_points">נקודות זיכוי נוספות</label>
        <input
          id="extra_credit_points"
          type="number"
          min="0"
          step="0.25"
          value={values.extra_credit_points}
          onChange={(event) => update('extra_credit_points', event.target.value)}
        />
        <div className="field-hint">מעבר לנקודות הבסיס — למשל ילדים או תואר</div>
      </div>

      <div>
        <label htmlFor="pension_employee_pct">הפרשה לפנסיה</label>
        <input
          id="pension_employee_pct"
          type="number"
          min="0"
          max="100"
          step="0.1"
          value={values.pension_employee_pct}
          onChange={(event) => update('pension_employee_pct', event.target.value)}
        />
        <div className="field-hint"><strong>אחוזים</strong> מהשכר (למשל 6)</div>
      </div>

      <div>
        <label htmlFor="keren_hishtalmut_monthly">קרן השתלמות</label>
        <input
          id="keren_hishtalmut_monthly"
          type="number"
          min="0"
          value={values.keren_hishtalmut_monthly}
          onChange={(event) => update('keren_hishtalmut_monthly', event.target.value)}
        />
        <div className="field-hint"><strong>₪ לחודש</strong>, חלק העובד</div>
      </div>

      <div>
        <label htmlFor="annual_donation">תרומות</label>
        <input
          id="annual_donation"
          type="number"
          min="0"
          value={values.annual_donation}
          onChange={(event) => update('annual_donation', event.target.value)}
        />
        <div className="field-hint"><strong>₪ לשנה</strong>, למוסדות מוכרים לפי סעיף 46</div>
      </div>
    </div>
  );
}
