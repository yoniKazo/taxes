import { AlertTriangle, Gavel, Sparkles } from 'lucide-react';
import { Fragment } from 'react';

import Badge, { VerdictBadge } from '../ui/Badge.jsx';
import EmptyState from '../ui/EmptyState.jsx';
import ErrorBanner from '../ui/ErrorBanner.jsx';
import Skeleton from '../ui/Skeleton.jsx';
import Stat from '../ui/Stat.jsx';

const JUDGE_LABELS = {
  context_relevance: 'רלוונטיות הקטעים',
  faithfulness: 'נאמנות למקור',
  answer_relevance: 'רלוונטיות התשובה',
  correctness: 'נכונות',
};

const REFUSAL_LABELS = {
  correct_refusal: ['סירוב נכון', 'good'],
  correct_answer: ['ענה כשצריך', 'good'],
  false_answer: ['ענה כשהיה צריך לסרב', 'bad'],
  false_refusal: ['סירב כשהייתה תשובה', 'bad'],
};

/**
 * Renders "[2]" as a control that scrolls to chunk 2.
 *
 * A citation the model invented -- a number past the chunks actually supplied --
 * is drawn in red instead of being silently rendered as ordinary text. That is
 * the deterministic guard from Task 4 made visible: it costs no LLM call and it
 * is exactly the kind of error a fluent answer hides.
 */
// Matches "[2]" and the grouped form "[1, 2, 8]" the model also produces. A
// pattern that only handled a lone number left grouped citations as plain text —
// unclickable, and with an out-of-range number in them showing no warning at all.
const CITATION_RE = /(\[\s*\d+(?:\s*,\s*\d+)*\s*\])/g;

function CitedAnswer({ text, chunkCount, onCite }) {
  return (
    <p className="answer-text">
      {text.split(CITATION_RE).map((part, index) => {
        if (!/^\[[\d\s,]+\]$/.test(part)) return <Fragment key={index}>{part}</Fragment>;
        const numbers = part.match(/\d+/g).map(Number);
        return numbers.map((number, i) => {
          const valid = number >= 1 && number <= chunkCount;
          return (
            <button
              key={`${index}-${i}`}
              type="button"
              className={valid ? 'citation-link' : 'citation-link invalid'}
              onClick={() => valid && onCite(number)}
              title={valid ? `הצג קטע ${number}` : `הקטע ${number} מעולם לא סופק למודל`}
            >
              {number}
            </button>
          );
        });
      })}
    </p>
  );
}

export default function GroundedAnswerPanel({
  answer, isPending, error, chunkCount, selectedCount,
  onAsk, onCite, canAsk,
  judge, judgePending, judgeError, onJudge, referenceAnswer,
  quotaRemaining,
}) {
  return (
    <>
      <div className="row between" style={{ marginBlockEnd: 'var(--space-4)' }}>
        <div className="row">
          <button type="button" className="primary" onClick={onAsk} disabled={!canAsk || isPending}>
            <Sparkles size={15} aria-hidden />
            {isPending ? 'מייצר תשובה…' : 'ענה מהקטעים שנבחרו'}
          </button>
          <span className="cost-hint">קריאה 1</span>
        </div>
        {quotaRemaining != null ? (
          <span className="muted">נותרו ~{quotaRemaining} קריאות היום</span>
        ) : null}
      </div>

      {selectedCount === 0 && chunkCount > 0 ? (
        <div className="panel-note warning">
          לא נבחר אף קטע. המערכת תקבל קונטקסט ריק — מערכת מעוגנת <strong>חייבת</strong> לסרב
          במצב הזה, וזה בדיוק מה ששווה לבדוק.
        </div>
      ) : null}

      {error ? <ErrorBanner message={error} /> : null}
      {isPending ? <Skeleton rows={3} /> : null}

      {!answer && !isPending && !error ? (
        <EmptyState
          icon={Sparkles}
          message="אחזר קטעים, סמן את אלה שברצונך לכלול, ואז בקש תשובה."
        />
      ) : null}

      {answer && !isPending ? (
        <>
          {answer.citation_flag ? (
            <div className="error-banner" role="alert">
              <AlertTriangle size={17} aria-hidden style={{ flexShrink: 0 }} />
              <span>
                <strong>ציטוט מומצא נתפס בקוד.</strong> המודל ציטט את הקטעים{' '}
                {answer.hallucinated_citations.join(', ')} מתוך {answer.chunks_used} שסופקו לו.
              </span>
            </div>
          ) : null}

          {answer.refusal_mismatch ? (
            <div className="panel-note warning">
              המודל קבע <code>answered=true</code> אבל החזיר את משפט הסירוב. הקוד סומך על
              הטקסט ולא על הדגל.
            </div>
          ) : null}

          <div className="row" style={{ marginBlockEnd: 'var(--space-3)' }}>
            <Badge tone={answer.answered ? 'good' : 'neutral'}>
              {answer.answered ? 'ענה' : 'סירב'}
            </Badge>
            <span className="muted">מבוסס על {answer.chunks_used} קטעים</span>
          </div>

          <CitedAnswer text={answer.answer} chunkCount={answer.chunks_used} onCite={onCite} />

          {answer.evidence?.length ? (
            <>
              <h3 className="drawer-section-title">ציטוט מילולי (evidence)</h3>
              {answer.evidence.map((quote, index) => (
                <blockquote key={index} className="evidence-quote">{quote}</blockquote>
              ))}
            </>
          ) : null}

          {answer.sources?.length ? (
            <>
              <h3 className="drawer-section-title" style={{ marginBlockStart: 'var(--space-4)' }}>
                מקורות
              </h3>
              <ul className="muted" style={{ margin: 0, paddingInlineStart: 'var(--space-5)' }}>
                {answer.sources.map((source, index) => <li key={index}>{source}</li>)}
              </ul>
            </>
          ) : null}

          <div className="stat-row" style={{ marginBlockStart: 'var(--space-4)' }}>
            <Stat label="זמן תגובה" value={`${Math.round(answer.latency_ms)} ms`} />
            <Stat label="טוקני קלט" value={answer.input_tokens} />
            <Stat label="טוקני פלט" value={answer.output_tokens} />
          </div>

          <div className="divider" />

          <div className="row between">
            <div className="row">
              <button type="button" onClick={onJudge} disabled={judgePending}>
                <Gavel size={15} aria-hidden />
                {judgePending ? 'שופט…' : 'הפעל שופטים'}
              </button>
              <span className="cost-hint">{referenceAnswer ? '4 קריאות' : '3 קריאות'} · ~20 שניות</span>
            </div>
            {!referenceAnswer ? (
              <span className="muted">
                אין תשובת ייחוס לשאלה הזו, ולכן correctness לא ייבדק
              </span>
            ) : null}
          </div>

          {judgeError ? <ErrorBanner message={judgeError} /> : null}
          {judgePending ? <Skeleton rows={2} /> : null}

          {judge ? (
            <div style={{ marginBlockStart: 'var(--space-3)' }}>
              <div className="panel-note">
                השופטים כאן מקבלים את השאלה גם ל-faithfulness — המכשיר המתוקן. המספרים
                ההיסטוריים בפאנל <strong>מדדי Task 5</strong> נמדדו עם הגרסה הישנה, שדירגה
                סירובים נכונים כ״גרוע״, ולכן פסיקה חיה כאן יכולה להיות שונה מהשורה השמורה.
              </div>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>קריטריון</th>
                      <th>פסיקה</th>
                      <th>נימוק</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(judge.verdicts).map(([key, value]) => (
                      <tr key={key}>
                        <td className="nowrap">{JUDGE_LABELS[key] ?? key}</td>
                        <td><VerdictBadge verdict={value.verdict} /></td>
                        <td>{value.explanation}</td>
                      </tr>
                    ))}
                    {judge.refusal_correctness ? (
                      <tr>
                        <td className="nowrap">נכונות הסירוב</td>
                        <td>
                          <Badge tone={REFUSAL_LABELS[judge.refusal_correctness]?.[1] ?? 'neutral'}>
                            {REFUSAL_LABELS[judge.refusal_correctness]?.[0] ?? judge.refusal_correctness}
                          </Badge>
                        </td>
                        <td className="muted">מחושב בקוד, ללא קריאת LLM</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </>
  );
}
