import { Search } from 'lucide-react';

import EmptyState from '../ui/EmptyState.jsx';
import ErrorBanner from '../ui/ErrorBanner.jsx';
import Skeleton from '../ui/Skeleton.jsx';
import ChunkCard from './ChunkCard.jsx';

// The three probes build_index.py runs on the CLI. Each was chosen to test a
// different retrieval property, so they are worth one click rather than retyping.
const SANITY_QUERIES = [
  { label: 'מס יסף (מופיע ב-3 מסמכים)', query: 'מהו שיעור מס היסף?' },
  { label: 'פטור ממס שבח (בית ברור אחד)', query: 'מהי תקרת הפטור ממס שבח לדירת מגורים יחידה?' },
  { label: 'קרן השתלמות (md + PDF)', query: 'מהי משכורת קובעת להפרשות לקרן השתלמות?' },
  { label: 'ארנונה (לא בקורפוס — חייב לסרב)', query: 'כיצד מחושבת הארנונה?' },
];

/**
 * Retrieval on its own, with the chunks laid out to be read.
 *
 * The tick boxes are the point: what is ticked here is exactly what the
 * generator receives, so unticking a chunk and re-asking shows the answer's
 * dependence on retrieval directly rather than by argument.
 */
export default function RetrievePanel({
  query, onQueryChange,
  k, onKChange,
  retriever, onRetrieverChange,
  denseWeight, onDenseWeightChange,
  onSubmit,
  result, isPending, error,
  includedIds, onToggleInclude, onSelectAll, onSelectNone,
}) {
  const chunks = result?.chunks ?? [];

  return (
    <>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <div className="row" style={{ flexWrap: 'nowrap', marginBlockEnd: 'var(--space-3)' }}>
          <input
            type="search"
            className="grow"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="שאל שאלת מיסוי…"
            aria-label="שאילתה"
          />
          <button type="submit" className="primary" disabled={!query.trim() || isPending}>
            <Search size={15} aria-hidden />
            {isPending ? 'מאחזר…' : 'אחזר'}
          </button>
        </div>

        <div className="field-grid" style={{ marginBlockEnd: 'var(--space-3)' }}>
          <div>
            <label htmlFor="rag-k">top-K: {k}</label>
            <input
              id="rag-k"
              type="range"
              min={1}
              max={12}
              value={k}
              onChange={(event) => onKChange(Number(event.target.value))}
            />
            <div className="field-hint">הבייסליין 5; ה-sweep מראה ש-k=8 מנקה את הפרוסה הקשה</div>
          </div>

          <div>
            <label htmlFor="rag-retriever">שיטת אחזור</label>
            <select
              id="rag-retriever"
              value={retriever}
              onChange={(event) => onRetrieverChange(event.target.value)}
            >
              <option value="dense">dense (embeddings)</option>
              <option value="hybrid">hybrid — dense + BM25</option>
            </select>
            <div className="field-hint">
              {retriever === 'hybrid'
                ? 'שילוב דירוגים; לא מחזיר ציון דמיון השוואתי'
                : 'ציון קוסינוס לכל צ׳אנק'}
            </div>
          </div>

          {retriever === 'hybrid' ? (
            <div>
              <label htmlFor="rag-dense-weight">משקל dense: {denseWeight}</label>
              <input
                id="rag-dense-weight"
                type="range"
                min={0}
                max={1}
                step={0.1}
                value={denseWeight}
                onChange={(event) => onDenseWeightChange(Number(event.target.value))}
              />
              <div className="field-hint">נמוך יותר = יותר BM25 (התאמה לקסיקלית מדויקת)</div>
            </div>
          ) : null}
        </div>
      </form>

      <div className="row" style={{ marginBlockEnd: 'var(--space-3)' }}>
        <span className="muted">שאילתות בדיקה:</span>
        {SANITY_QUERIES.map((item) => (
          <button
            key={item.query}
            type="button"
            className="ghost"
            onClick={() => { onQueryChange(item.query); onSubmit(item.query); }}
            title={item.query}
          >
            {item.label}
          </button>
        ))}
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {isPending ? <Skeleton rows={4} /> : null}

      {!isPending && !error && chunks.length === 0 ? (
        <EmptyState
          icon={Search}
          message="הרץ שאילתה כדי לראות אילו צ'אנקים חוזרים מהקורפוס."
        />
      ) : null}

      {chunks.length > 0 ? (
        <>
          <div className="row between" style={{ marginBlockEnd: 'var(--space-3)' }}>
            <strong>
              נבחרו {includedIds.size} מתוך {chunks.length} צ'אנקים לקונטקסט
            </strong>
            <div className="row">
              <button type="button" className="ghost" onClick={onSelectAll}>בחר הכל</button>
              <button type="button" className="ghost" onClick={onSelectNone}>נקה בחירה</button>
            </div>
          </div>

          <div className="chunk-list">
            {chunks.map((chunk) => (
              <ChunkCard
                key={chunk.rank}
                id={`chunk-${chunk.rank}`}
                chunk={chunk}
                query={result?.query}
                included={includedIds.has(chunk.rank)}
                onToggleInclude={() => onToggleInclude(chunk.rank)}
              />
            ))}
          </div>
        </>
      ) : null}
    </>
  );
}
