export default function SharedFieldsForm({ values, onChange }) {
  function update(field, value) {
    onChange({ ...values, [field]: value });
  }

  return (
    <div className="shared-fields-form">
      <h2>פרטים נוספים</h2>
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
        </div>
        <div>
          <label htmlFor="pension_employee_pct">אחוז הפרשה לפנסיה (עובד)</label>
          <input
            id="pension_employee_pct"
            type="number"
            min="0"
            max="100"
            step="0.1"
            value={values.pension_employee_pct}
            onChange={(event) => update('pension_employee_pct', event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="keren_hishtalmut_monthly">הפקדה חודשית לקרן השתלמות</label>
          <input
            id="keren_hishtalmut_monthly"
            type="number"
            min="0"
            step="1"
            value={values.keren_hishtalmut_monthly}
            onChange={(event) => update('keren_hishtalmut_monthly', event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="annual_donation">תרומות שנתיות</label>
          <input
            id="annual_donation"
            type="number"
            min="0"
            step="1"
            value={values.annual_donation}
            onChange={(event) => update('annual_donation', event.target.value)}
          />
        </div>
      </div>
    </div>
  );
}
