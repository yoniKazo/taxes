import { VerdictBadge } from '../ui/Badge.jsx';
import DataTable from '../ui/DataTable.jsx';
import EmptyState from '../ui/EmptyState.jsx';

/** Task 5 (a), (b), (c) -- the three findings the assignment requires. */
export default function AnalysisPanel({ data }) {
  const worseColumns = [
    { key: 'id', label: '#', numeric: true, width: 48 },
    { key: 'question', label: 'שאלה', render: (r) => <div className="cell-clamp">{r.question}</div> },
    { key: 'baseline_answer', label: 'בייסליין', render: (r) => <div className="cell-clamp">{r.baseline_answer}</div> },
    { key: 'rag_answer', label: 'RAG', render: (r) => <div className="cell-clamp">{r.rag_answer}</div> },
    { key: 'rag_correctness', label: 'נכונות RAG', render: (r) => <VerdictBadge verdict={r.rag_correctness} /> },
  ];

  const worstColumns = [
    { key: 'id', label: '#', numeric: true, width: 48 },
    { key: 'question', label: 'שאלה', render: (r) => <div className="cell-clamp">{r.question}</div> },
    { key: 'category', label: 'קטגוריה' },
    { key: 'mean_judge', label: 'ציון ממוצע', numeric: true, render: (r) => r.mean_judge.toFixed(2) },
    { key: 'hit_at_k', label: 'hit@k', render: (r) => (r.hit_at_k == null ? '—' : r.hit_at_k ? '✓' : '✗') },
    { key: 'rag_correctness', label: 'נכונות', render: (r) => <VerdictBadge verdict={r.rag_correctness} /> },
  ];

  return (
    <div className="stack" style={{ gap: 'var(--space-6)' }}>
      <section>
        <h3>(א) שאלה שבה RAG הרע לעומת הבייסליין</h3>
        <p className="muted">
          גראונדינג חוסם הזיות במחיר של הגבלת המערכת לתקרה של הקורפוס. כשהצ׳אנק שאוחזר פחות
          מלא מהידע שהמודל צבר באימון, המודל מציית להוראה ומשמיט את מה שחסר.
          <strong> RAG אינו שדרוג חינם; הוא מחליף את שגיאות המודל בשגיאות הקורפוס.</strong>
        </p>
        <DataTable columns={worseColumns} rows={data?.rag_worse_than_baseline ?? []} />
      </section>

      <section>
        <h3>(ב) ״תשובה נכונה, צינור שבור״</h3>
        {data?.right_answer_broken_pipeline_is_empty ? (
          <>
            <p className="muted">
              חיפוש של <code>correctness=good</code> יחד עם <code>hit@k=false</code> החזיר{' '}
              <strong>0 שורות</strong>. הסיבה מבנית ולא מקרית: hit@k=0.969 פירושו ששאלה אחת
              בלבד החטיאה את האחזור, ובה המערכת <strong>סירבה</strong> במקום לענות נכון מהזיכרון,
              ולכן הנכונות נכשלה. לא נותרה הזדמנות לתרחיש להתרחש.
            </p>
            <EmptyState
              title="אפס שורות — וזו תוצאה"
              message="היעדר המקרה הוא הממצא, לא טבלה ריקה."
            />
          </>
        ) : (
          <DataTable columns={worseColumns} rows={data?.right_answer_broken_pipeline ?? []} />
        )}
      </section>

      <section>
        <h3>(ג) חמש התשובות הגרועות — אחזור או יצירה?</h3>
        <p className="muted">
          הספירה בפועל: <strong>2 כשלי אחזור</strong>, <strong>1 מגבלת קורפוס</strong>,{' '}
          <strong>2 ארטיפקטים של מדידה</strong> (סירובים נכונים שהשופט דירג כגרועים, כי הוא נבנה
          בלי לראות את השאלה). אין אף כשל יצירה אמיתי ברשימה — ולכן ניסוי 1 כוון ל-K ולא לפרומפט.
        </p>
        <DataTable columns={worstColumns} rows={data?.worst_rows ?? []} />
      </section>
    </div>
  );
}
