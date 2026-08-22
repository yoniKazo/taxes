import { ChevronDown, ChevronUp } from 'lucide-react';
import { useMemo, useState } from 'react';

import Badge from '../ui/Badge.jsx';
import { ScoreMeter } from '../ui/Stat.jsx';

/** Words too short or too common to be worth highlighting. */
const STOP_WORDS = new Set(['מהי', 'מהו', 'האם', 'כיצד', 'איזה', 'אילו', 'של', 'על', 'עם', 'לפי', 'את', 'מה']);

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Highlight the query's own terms inside the chunk.
 *
 * This is the fastest way to see WHY something was retrieved -- or that it was
 * retrieved with no lexical overlap at all, which is the interesting case.
 */
function highlight(text, query) {
  if (!query) return text;
  const terms = query
    .split(/[\s,.?!"'()]+/)
    .map((t) => t.trim())
    .filter((t) => t.length > 2 && !STOP_WORDS.has(t));
  if (terms.length === 0) return text;

  const pattern = new RegExp(`(${terms.map(escapeRegExp).join('|')})`, 'g');
  return text.split(pattern).map((part, index) =>
    terms.includes(part) ? <mark key={index}>{part}</mark> : part,
  );
}

export default function ChunkCard({
  chunk,
  query,
  included,
  onToggleInclude,
  highlighted = false,
  id,
}) {
  const [expanded, setExpanded] = useState(false);
  const body = useMemo(() => highlight(chunk.text, query), [chunk.text, query]);
  const selectable = onToggleInclude != null;

  return (
    <article
      id={id}
      className={[
        'chunk-card',
        selectable ? (included ? 'included' : 'excluded') : '',
        highlighted ? 'highlight' : '',
      ].filter(Boolean).join(' ')}
    >
      <header className="chunk-head">
        {chunk.rank != null ? <span className="chunk-rank">{chunk.rank}</span> : null}
        <div className="grow">
          <div className="chunk-doc">{chunk.doc_name}</div>
          <div className="chunk-where">
            {chunk.location}
            {chunk.chars != null ? ` · ${chunk.chars} תווים` : ''}
          </div>
        </div>
        {chunk.doc_format ? (
          <Badge tone={chunk.doc_format === 'pdf' ? 'warning' : 'info'}>{chunk.doc_format}</Badge>
        ) : null}
        {chunk.rank != null ? <ScoreMeter score={chunk.score} /> : null}
        {selectable ? (
          <label className="chunk-include">
            <input type="checkbox" checked={included} onChange={onToggleInclude} />
            כלול בקונטקסט
          </label>
        ) : null}
      </header>

      <div className={expanded ? 'chunk-text expanded' : 'chunk-text'}>{body}</div>

      {chunk.chars > 600 ? (
        <button
          type="button"
          className="ghost"
          onClick={() => setExpanded((v) => !v)}
          style={{ width: '100%', borderRadius: 0, borderBlockStart: '1px solid var(--border)' }}
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {expanded ? 'כווץ' : 'הצג הכל'}
        </button>
      ) : null}
    </article>
  );
}
