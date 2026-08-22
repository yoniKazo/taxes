import { useQuery } from '@tanstack/react-query';
import { Shuffle } from 'lucide-react';
import { useState } from 'react';

import { browseRagChunks } from '../../api/client.js';
import EmptyState from '../ui/EmptyState.jsx';
import ErrorBanner from '../ui/ErrorBanner.jsx';
import Skeleton from '../ui/Skeleton.jsx';
import ChunkCard from './ChunkCard.jsx';

const PAGE_SIZE = 6;

/**
 * Task 3's "actually look at it" step, which the assignment is emphatic about:
 * print chunks and read them before theorising about retrieval.
 *
 * The PDF filter is the useful one. The markdown tables survived chunking
 * intact; the PDF lost spaces before numbers ("סעיף10") and flattened its
 * tables into space-separated lines. Reading the two side by side is what makes
 * the parsing damage a fact rather than a claim in a write-up.
 */
export default function ChunkBrowserPanel({ indexId, documents }) {
  const [docName, setDocName] = useState('');
  const [docFormat, setDocFormat] = useState('');
  const [search, setSearch] = useState('');
  const [offset, setOffset] = useState(0);
  const [seed, setSeed] = useState(null);

  const params = {
    index_id: indexId,
    doc_name: docName || undefined,
    doc_format: docFormat || undefined,
    search: search || undefined,
    offset: seed == null ? offset : undefined,
    limit: seed == null ? PAGE_SIZE : 10,
    seed: seed ?? undefined,
  };

  const { data, isPending, error } = useQuery({
    queryKey: ['rag-chunks', params],
    queryFn: () => browseRagChunks(params),
  });

  const resetPaging = () => {
    setOffset(0);
    setSeed(null);
  };

  return (
    <>
      <div className="toolbar">
        <select
          value={docName}
          onChange={(event) => { setDocName(event.target.value); resetPaging(); }}
          style={{ maxWidth: 240 }}
          aria-label="סנן לפי מסמך"
        >
          <option value="">כל המסמכים</option>
          {documents.map((doc) => (
            <option key={doc.doc_name} value={doc.doc_name}>{doc.doc_name}</option>
          ))}
        </select>

        <div className="pill-group">
          {[['', 'הכל'], ['md', 'Markdown'], ['pdf', 'PDF']].map(([value, label]) => (
            <button
              key={value || 'all'}
              type="button"
              className={docFormat === value ? 'active' : ''}
              onClick={() => { setDocFormat(value); resetPaging(); }}
            >
              {label}
            </button>
          ))}
        </div>

        <input
          type="search"
          className="search-input"
          value={search}
          onChange={(event) => { setSearch(event.target.value); resetPaging(); }}
          placeholder="חיפוש בטקסט הצ'אנקים…"
          style={{ maxWidth: 240 }}
          aria-label="חיפוש בטקסט"
        />

        <button
          type="button"
          onClick={() => setSeed(Math.floor(Math.random() * 100000))}
          title="דגום 10 צ'אנקים אקראיים — צעד ה-Task 3 של קריאה בעיניים"
        >
          <Shuffle size={14} aria-hidden />
          דגימה אקראית
        </button>

        <span className="muted nowrap" style={{ marginInlineStart: 'auto' }}>
          {data ? `${data.total} צ'אנקים` : ''}
        </span>
      </div>

      {error ? <ErrorBanner message={error.message} /> : null}
      {isPending ? <Skeleton rows={4} /> : null}

      {data && data.chunks.length === 0 ? (
        <EmptyState message="אין צ'אנקים שתואמים לסינון." />
      ) : null}

      {data && data.chunks.length > 0 ? (
        <>
          <div className="chunk-list">
            {data.chunks.map((chunk) => (
              <ChunkCard key={chunk.chunk_index} chunk={chunk} query={search} />
            ))}
          </div>

          {seed == null ? (
            <div className="row" style={{ marginBlockStart: 'var(--space-4)', justifyContent: 'center' }}>
              <button type="button" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}>
                הקודם
              </button>
              <span className="muted">
                {offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} מתוך {data.total}
              </span>
              <button
                type="button"
                disabled={offset + PAGE_SIZE >= data.total}
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
              >
                הבא
              </button>
            </div>
          ) : (
            <div className="row" style={{ marginBlockStart: 'var(--space-4)', justifyContent: 'center' }}>
              <span className="muted">דגימה אקראית (seed {seed})</span>
              <button type="button" className="ghost" onClick={resetPaging}>חזור לדפדוף</button>
            </div>
          )}
        </>
      ) : null}
    </>
  );
}
