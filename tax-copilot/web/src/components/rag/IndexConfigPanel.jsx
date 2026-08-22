import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Eye, Hammer, Lock, Target, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

import { buildRagIndex, deleteRagIndex, evaluateRagRetrieval, previewRagChunks } from '../../api/client.js';
import { useJob } from '../../hooks/useJob.js';
import Badge from '../ui/Badge.jsx';
import ConfirmButton from '../ui/ConfirmButton.jsx';
import ProgressBar from '../ui/ProgressBar.jsx';
import Stat from '../ui/Stat.jsx';

const E5 = 'intfloat/multilingual-e5-small';
const BGE = 'BAAI/bge-small-en-v1.5';

const CHUNK_PRESETS = [
  [500, 100],
  [1000, 150],
  [1500, 200],
];

/**
 * Build an index from a chosen slice of the corpus, then measure whether it
 * actually retrieves better -- for free.
 *
 * The order matters: preview (instant, no embedding) -> build (CPU-minutes) ->
 * hit@k (32 embedded queries, still no API calls). The assignment is explicit
 * that hit-rate is the metric to sweep against precisely because it costs
 * nothing, so tuning here never touches the quota.
 */
export default function IndexConfigPanel({
  indexes, activeIndexId, onSelectIndex,
  selectedDocs, chunkSize, overlap, embeddingModel,
  onChunkSizeChange, onOverlapChange, onEmbeddingModelChange,
  k, retriever, denseWeight, onHitRateResult,
}) {
  const queryClient = useQueryClient();
  const [preview, setPreview] = useState(null);

  const previewMutation = useMutation({
    mutationFn: () => previewRagChunks({
      doc_names: selectedDocs, chunk_size: chunkSize, chunk_overlap: overlap,
    }),
    onSuccess: setPreview,
    onError: (error) => toast.error(error.message),
  });

  const buildJob = useJob({
    start: () => buildRagIndex({
      doc_names: selectedDocs,
      chunk_size: chunkSize,
      chunk_overlap: overlap,
      embedding_model: embeddingModel,
    }),
    successMessage: 'האינדקס נבנה.',
    onDone: (result) => {
      queryClient.invalidateQueries({ queryKey: ['rag-indexes'] });
      if (result?.index_id) onSelectIndex(result.index_id);
    },
  });

  const hitRateJob = useJob({
    start: () => evaluateRagRetrieval({
      index_id: activeIndexId, k, retriever, dense_weight: denseWeight,
    }),
    successMessage: 'hit@k חושב.',
    onDone: onHitRateResult,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteRagIndex,
    onSuccess: () => {
      toast.success('האינדקס נמחק.');
      onSelectIndex('default');
      queryClient.invalidateQueries({ queryKey: ['rag-indexes'] });
    },
    onError: (error) => toast.error(error.message),
  });

  const active = indexes.find((index) => index.index_id === activeIndexId);
  const noDocs = selectedDocs.length === 0;

  return (
    <>
      <div style={{ marginBlockEnd: 'var(--space-4)' }}>
        <label htmlFor="active-index">אינדקס פעיל</label>
        <div className="row" style={{ flexWrap: 'nowrap' }}>
          <select
            id="active-index"
            className="grow"
            value={activeIndexId}
            onChange={(event) => onSelectIndex(event.target.value)}
          >
            {indexes.map((index) => (
              <option key={index.index_id} value={index.index_id}>
                {index.label} · {index.chunk_count} צ'אנקים
                {index.read_only ? ' (מוגן)' : ''}
              </option>
            ))}
          </select>
          {active && !active.read_only ? (
            <ConfirmButton
              onConfirm={() => deleteMutation.mutate(active.index_id)}
              title="מחק את האינדקס הזה"
            >
              <Trash2 size={14} aria-hidden />
            </ConfirmButton>
          ) : null}
        </div>
        {active?.read_only ? (
          <div className="field-hint row" style={{ gap: 4 }}>
            <Lock size={11} aria-hidden />
            זהו האינדקס הקנוני של המטלה. הוא לקריאה בלבד — בנייה יוצרת אינדקס חדש לצידו.
          </div>
        ) : null}
      </div>

      <div className="divider" />

      <div className="field-grid">
        <div>
          <label htmlFor="chunk-size">גודל צ'אנק</label>
          <input
            id="chunk-size"
            type="number"
            min={100}
            max={4000}
            step={50}
            value={chunkSize}
            onChange={(event) => onChunkSizeChange(Number(event.target.value))}
          />
          <div className="row" style={{ marginBlockStart: 'var(--space-2)', gap: 4 }}>
            {CHUNK_PRESETS.map(([size, over]) => (
              <button
                key={size}
                type="button"
                className="ghost"
                onClick={() => { onChunkSizeChange(size); onOverlapChange(over); }}
              >
                {size}/{over}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label htmlFor="chunk-overlap">חפיפה</label>
          <input
            id="chunk-overlap"
            type="number"
            min={0}
            max={1000}
            step={10}
            value={overlap}
            onChange={(event) => onOverlapChange(Number(event.target.value))}
          />
          <div className="field-hint">1000/150 הוא הבייסליין של המטלה</div>
        </div>

        <div>
          <label htmlFor="embedding-model">מודל embedding</label>
          <select
            id="embedding-model"
            value={embeddingModel}
            onChange={(event) => onEmbeddingModelChange(event.target.value)}
          >
            <option value={E5}>multilingual-e5-small</option>
            <option value={BGE}>bge-small-en-v1.5</option>
          </select>
          {embeddingModel === BGE ? (
            <div className="field-hint row" style={{ gap: 4, color: 'var(--warning-fg)' }}>
              <AlertTriangle size={11} aria-hidden />
              אנגלית בלבד — hit@k צונח מ-0.969 ל-0.719 על הקורפוס העברי
            </div>
          ) : (
            <div className="field-hint">רב-לשוני; הבחירה התפעולית של המטלה</div>
          )}
        </div>
      </div>

      <div className="row" style={{ marginBlockStart: 'var(--space-4)' }}>
        <button
          type="button"
          onClick={() => previewMutation.mutate()}
          disabled={noDocs || previewMutation.isPending}
        >
          <Eye size={15} aria-hidden />
          {previewMutation.isPending ? 'מחשב…' : 'תצוגה מקדימה'}
        </button>
        <button
          type="button"
          className="primary"
          onClick={() => buildJob.start()}
          disabled={noDocs || buildJob.running}
        >
          <Hammer size={15} aria-hidden />
          {buildJob.running ? 'בונה…' : 'בנה אינדקס'}
        </button>
        <span className="muted">
          {noDocs ? 'לא נבחר אף מסמך בפאנל הקורפוס' : `${selectedDocs.length} מסמכים נבחרו`}
        </span>
      </div>

      {preview ? (
        <div className="stat-row" style={{ marginBlockStart: 'var(--space-4)' }}>
          <Stat label="צ'אנקים" value={preview.chunk_count} caption="בלי embedding — מיידי" />
          <Stat label="אורך ממוצע" value={`${Math.round(preview.mean_chars)} תווים`} />
          <Stat label="הקצר ביותר" value={preview.min_chars} />
          <Stat label="הארוך ביותר" value={preview.max_chars} />
        </div>
      ) : null}

      {buildJob.running ? (
        <div style={{ marginBlockStart: 'var(--space-4)' }}>
          <ProgressBar
            phase={buildJob.job?.phase ?? 'מתחיל…'}
            done={buildJob.job?.done ?? 0}
            total={buildJob.job?.total ?? 0}
            onCancel={buildJob.cancel}
          />
        </div>
      ) : null}

      <div className="divider" />

      <div className="row between">
        <div className="row">
          <button type="button" onClick={() => hitRateJob.start()} disabled={hitRateJob.running}>
            <Target size={15} aria-hidden />
            {hitRateJob.running ? 'מודד…' : `מדוד hit@k (k=${k})`}
          </button>
          <Badge tone="good">0 קריאות LLM</Badge>
        </div>
        <span className="muted">32 שאלות בנות-מענה · ~30 שניות</span>
      </div>

      {hitRateJob.running ? (
        <div style={{ marginBlockStart: 'var(--space-3)' }}>
          <ProgressBar
            phase={hitRateJob.job?.phase ?? 'מתחיל…'}
            done={hitRateJob.job?.done ?? 0}
            total={hitRateJob.job?.total ?? 0}
            onCancel={hitRateJob.cancel}
          />
        </div>
      ) : null}

      {hitRateJob.result ? (
        <div className="stat-row" style={{ marginBlockStart: 'var(--space-3)' }}>
          <Stat label="hit@k כולל" value={hitRateJob.result.hit_at_k.toFixed(3)} hero />
          <Stat label="קלות" value={hitRateJob.result.hit_at_k_easy?.toFixed(3) ?? '—'} />
          <Stat
            label="קשות"
            value={hitRateJob.result.hit_at_k_hard?.toFixed(3) ?? '—'}
            caption="n=4 — כל שאלה שווה 25 נק׳ אחוז"
          />
          <Stat
            label="החטאות"
            value={hitRateJob.result.misses.length}
            caption={hitRateJob.result.misses.length ? `שאלות ${hitRateJob.result.misses.join(', ')}` : 'אין'}
          />
        </div>
      ) : null}
    </>
  );
}
