/**
 * כל השדות כאן שנתיים -- כולל קרן השתלמות, שעד לאחרונה הוזנה כסכום חודשי
 * (ראו history: השדה נקרא היום keren_hishtalmut_annual, לא _monthly).
 */
export default function DeductionsForm({ values, onChange }) {
  const update = (field, value) => onChange({ ...values, [field]: value });

  return (
    <div className="field-grid">
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
        <label htmlFor="keren_hishtalmut_annual">קרן השתלמות</label>
        <input
          id="keren_hishtalmut_annual"
          type="number"
          min="0"
          value={values.keren_hishtalmut_annual}
          onChange={(event) => update('keren_hishtalmut_annual', event.target.value)}
        />
        <div className="field-hint"><strong>₪ לשנה</strong>, חלק העובד</div>
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
