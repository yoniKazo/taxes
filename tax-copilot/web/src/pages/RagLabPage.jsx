import { useMutation, useQuery } from '@tanstack/react-query';
import {
  BarChart3, BookOpen, Database, FileSearch, FlaskConical, Gauge, Layers,
  ListChecks, Microscope, Search, Sparkles,
} from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';

import {
  answerWithRag, getRagAnalysis, getRagBaseline, getRagCorpus, getRagEvalSet,
  getRagExperiments, getRagIndexes, getRagMetrics, getRagPerQuestion, getRagQuota,
  getRagSweeps, judgeRagAnswer, retrieveRagChunks,
} from '../api/client.js';
import AnalysisPanel from '../components/rag/AnalysisPanel.jsx';
import BaselinePanel from '../components/rag/BaselinePanel.jsx';
import ChunkBrowserPanel from '../components/rag/ChunkBrowserPanel.jsx';
import CorpusPanel from '../components/rag/CorpusPanel.jsx';
import EvalSetPanel from '../components/rag/EvalSetPanel.jsx';
import ExperimentsPanel from '../components/rag/ExperimentsPanel.jsx';
import GroundedAnswerPanel from '../components/rag/GroundedAnswerPanel.jsx';
import IndexConfigPanel from '../components/rag/IndexConfigPanel.jsx';
import MetricsPanel from '../components/rag/MetricsPanel.jsx';
import PerQuestionPanel from '../components/rag/PerQuestionPanel.jsx';
import RetrievePanel from '../components/rag/RetrievePanel.jsx';
import SweepsPanel from '../components/rag/SweepsPanel.jsx';
import Panel from '../components/ui/Panel.jsx';
import PanelPicker from '../components/ui/PanelPicker.jsx';
import ProcessExplainer from '../components/ui/ProcessExplainer.jsx';
import { RAG_EXPLAINERS } from '../constants/ragExplainers.js';
import { usePanelPrefs } from '../hooks/usePanelPrefs.js';

// Panels the page can show. `defaultVisible: false` keeps the first load about
// the live playground; everything else is one tick away in the picker.
const PANELS = [
  { id: 'retrieve', title: 'מגרש משחקים — אחזור', icon: Search },
  { id: 'answer', title: 'תשובה מעוגנת', icon: Sparkles, cost: 'עולה קריאות' },
  { id: 'index', title: 'קונפיגורציית אינדקס', icon: Layers },
  { id: 'corpus', title: 'הקורפוס', icon: Database },
  { id: 'chunks', title: "דפדפן צ'אנקים", icon: FileSearch },
  { id: 'evalset', title: 'מערך ההערכה', icon: ListChecks, defaultVisible: false },
  { id: 'baseline', title: 'בייסליין ללא RAG', icon: BookOpen, defaultVisible: false },
  { id: 'metrics', title: 'מדדי Task 5 — RAG מול בייסליין', icon: Gauge },
  { id: 'perquestion', title: 'פירוט לפי שאלה', icon: Microscope, defaultVisible: false },
  { id: 'sweeps', title: 'Task 6 — sweeps', icon: BarChart3 },
  { id: 'experiments', title: 'Task 6 — ניסויים', icon: FlaskConical, defaultVisible: false },
  { id: 'analysis', title: 'ניתוח (א)/(ב)/(ג)', icon: Microscope, defaultVisible: false },
];

const DEFAULT_INDEX = 'default';

export default function RagLabPage() {
  const prefs = usePanelPrefs('rag', PANELS);
  const [searchParams, setSearchParams] = useSearchParams();

  // Retrieval settings live in the URL so a result is reproducible and shareable
  // rather than trapped in component state.
  const query = searchParams.get('q') ?? '';
  const k = Number(searchParams.get('k') ?? 5);
  const indexId = searchParams.get('index') ?? DEFAULT_INDEX;
  const retriever = searchParams.get('retriever') ?? 'dense';
  const denseWeight = Number(searchParams.get('w') ?? 0.5);

  const setParam = useCallback(
    (patch) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          Object.entries(patch).forEach(([key, value]) => {
            if (value === null || value === undefined || value === '') next.delete(key);
            else next.set(key, String(value));
          });
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  // null = "the whole corpus" (the initial state, before the user touches
  // anything). An empty ARRAY means they deliberately unticked everything, which
  // must stay empty -- treating [] as "all" made unticking the last document
  // silently re-select all six.
  const [selectedDocs, setSelectedDocs] = useState(null);
  const [chunkSize, setChunkSize] = useState(1000);
  const [overlap, setOverlap] = useState(150);
  const [embeddingModel, setEmbeddingModel] = useState('intfloat/multilingual-e5-small');
  const [includedRanks, setIncludedRanks] = useState(new Set());
  const [liveHitRate, setLiveHitRate] = useState(null);
  const [referenceAnswer, setReferenceAnswer] = useState(null);
  const [answerable, setAnswerable] = useState(null);

  // --- data ---

  const corpus = useQuery({ queryKey: ['rag-corpus'], queryFn: getRagCorpus });
  const allDocNames = useMemo(
    () => (corpus.data?.documents ?? []).map((doc) => doc.doc_name),
    [corpus.data],
  );
  const effectiveDocs = selectedDocs ?? allDocNames;
  const indexes = useQuery({ queryKey: ['rag-indexes'], queryFn: getRagIndexes });
  const evalSet = useQuery({
    queryKey: ['rag-eval-set'], queryFn: getRagEvalSet, enabled: prefs.isVisible('evalset'),
  });
  const baseline = useQuery({
    queryKey: ['rag-baseline'], queryFn: getRagBaseline, enabled: prefs.isVisible('baseline'),
  });
  const metrics = useQuery({
    queryKey: ['rag-metrics'], queryFn: getRagMetrics, enabled: prefs.isVisible('metrics'),
  });
  const perQuestion = useQuery({
    queryKey: ['rag-per-question'], queryFn: getRagPerQuestion, enabled: prefs.isVisible('perquestion'),
  });
  const sweeps = useQuery({
    queryKey: ['rag-sweeps'], queryFn: getRagSweeps, enabled: prefs.isVisible('sweeps'),
  });
  const experiments = useQuery({
    queryKey: ['rag-experiments'], queryFn: getRagExperiments, enabled: prefs.isVisible('experiments'),
  });
  const analysis = useQuery({
    queryKey: ['rag-analysis'], queryFn: getRagAnalysis, enabled: prefs.isVisible('analysis'),
  });
  const quota = useQuery({ queryKey: ['rag-quota'], queryFn: getRagQuota, staleTime: 0 });

  // --- retrieve / answer / judge ---

  const retrieveMutation = useMutation({
    mutationFn: (payload) => retrieveRagChunks(payload),
    onSuccess: (data) => {
      // Everything retrieved starts included; the interesting act is taking
      // chunks AWAY and seeing the answer change.
      setIncludedRanks(new Set(data.chunks.map((chunk) => chunk.rank)));
      answerMutation.reset();
      judgeMutation.reset();
    },
    onError: (error) => toast.error(error.message),
  });

  const answerMutation = useMutation({
    mutationFn: (payload) => answerWithRag(payload),
    onSuccess: () => quota.refetch(),
    onError: (error) => toast.error(error.message),
  });

  const judgeMutation = useMutation({
    mutationFn: (payload) => judgeRagAnswer(payload),
    onSuccess: () => quota.refetch(),
    onError: (error) => toast.error(error.message),
  });

  const runRetrieve = useCallback(
    (overrideQuery) => {
      const q = typeof overrideQuery === 'string' ? overrideQuery : query;
      if (!q.trim()) return;
      retrieveMutation.mutate({
        query: q, k, index_id: indexId, retriever, dense_weight: denseWeight,
      });
    },
    [query, k, indexId, retriever, denseWeight, retrieveMutation],
  );

  const selectedChunks = useMemo(
    () => (retrieveMutation.data?.chunks ?? []).filter((chunk) => includedRanks.has(chunk.rank)),
    [retrieveMutation.data, includedRanks],
  );

  const askGrounded = useCallback(() => {
    answerMutation.mutate({
      query: retrieveMutation.data?.query ?? query,
      index_id: indexId,
      k,
      chunks: selectedChunks.map((chunk) => ({
        text: chunk.text,
        doc_name: chunk.doc_name,
        page: chunk.page,
        section: chunk.section,
        chunk_index: chunk.chunk_index,
      })),
    });
  }, [answerMutation, retrieveMutation.data, query, indexId, k, selectedChunks]);

  const runJudge = useCallback(() => {
    const answer = answerMutation.data;
    if (!answer) return;
    judgeMutation.mutate({
      question: answer.query,
      answer: answer.answer,
      chunks: selectedChunks.map((chunk) => chunk.text),
      reference_answer: referenceAnswer ?? undefined,
      answerable: answerable ?? undefined,
      answered: answer.answered,
    });
  }, [answerMutation.data, judgeMutation, selectedChunks, referenceAnswer, answerable]);

  const useEvalQuestion = useCallback(
    (row) => {
      setParam({ q: row.question });
      setReferenceAnswer(row.reference_answer || null);
      setAnswerable(row.answerable);
      runRetrieveWith(row.question);
      document.getElementById('panel-retrieve')?.scrollIntoView({ behavior: 'smooth' });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [setParam, k, indexId, retriever, denseWeight],
  );

  function runRetrieveWith(q) {
    retrieveMutation.mutate({ query: q, k, index_id: indexId, retriever, dense_weight: denseWeight });
  }

  const scrollToChunk = useCallback((number) => {
    const element = document.getElementById(`chunk-${number}`);
    element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    element?.classList.add('highlight');
    setTimeout(() => element?.classList.remove('highlight'), 1600);
  }, []);

  const panelProps = (id) => ({
    collapsed: prefs.isCollapsed(id),
    onToggleCollapsed: () => prefs.toggleCollapsed(id),
    onHide: () => prefs.toggleVisible(id),
  });

  const quotaData = quota.data;
  const quotaLow = quotaData && quotaData.remaining < 50;

  return (
    <div className="app-main">
      <div className="row between" style={{ marginBlockEnd: 'var(--space-4)' }}>
        <div>
          <h1>מעבדת RAG</h1>
          <p className="muted" style={{ margin: 0 }}>
            מטלה 3 — אחזור, עיגון והערכה מעל קורפוס המיסוי הישראלי
          </p>
        </div>
        <div className="row">
          {quotaData ? (
            <span className={quotaLow ? 'quota-chip warning' : 'quota-chip'}>
              קריאות היום: {quotaData.used_today} / {quotaData.daily_limit}
            </span>
          ) : null}
          <PanelPicker panels={PANELS} prefs={prefs} />
        </div>
      </div>

      {prefs.isVisible('retrieve') ? (
        <div id="panel-retrieve">
          <Panel
            title="מגרש משחקים — אחזור"
            subtitle="0 קריאות LLM"
            icon={Search}
            {...panelProps('retrieve')}
          >
            <ProcessExplainer id="rag-retrieve" {...RAG_EXPLAINERS.retrieve} />
            <RetrievePanel
              query={query}
              onQueryChange={(value) => setParam({ q: value })}
              k={k}
              onKChange={(value) => setParam({ k: value })}
              retriever={retriever}
              onRetrieverChange={(value) => setParam({ retriever: value })}
              denseWeight={denseWeight}
              onDenseWeightChange={(value) => setParam({ w: value })}
              onSubmit={runRetrieve}
              result={retrieveMutation.data}
              isPending={retrieveMutation.isPending}
              error={retrieveMutation.error?.message}
              includedIds={includedRanks}
              onToggleInclude={(rank) =>
                setIncludedRanks((current) => {
                  const next = new Set(current);
                  if (next.has(rank)) next.delete(rank);
                  else next.add(rank);
                  return next;
                })
              }
              onSelectAll={() =>
                setIncludedRanks(new Set((retrieveMutation.data?.chunks ?? []).map((c) => c.rank)))
              }
              onSelectNone={() => setIncludedRanks(new Set())}
            />
          </Panel>
        </div>
      ) : null}

      {prefs.isVisible('answer') ? (
        <Panel
          title="תשובה מעוגנת"
          subtitle="עולה קריאות LLM"
          icon={Sparkles}
          {...panelProps('answer')}
        >
          <ProcessExplainer id="rag-answer" {...RAG_EXPLAINERS.answer} />
          <GroundedAnswerPanel
            answer={answerMutation.data}
            isPending={answerMutation.isPending}
            error={answerMutation.error?.message}
            chunkCount={retrieveMutation.data?.chunks?.length ?? 0}
            selectedCount={includedRanks.size}
            canAsk={Boolean(retrieveMutation.data)}
            onAsk={askGrounded}
            onCite={scrollToChunk}
            judge={judgeMutation.data}
            judgePending={judgeMutation.isPending}
            judgeError={judgeMutation.error?.message}
            onJudge={runJudge}
            referenceAnswer={referenceAnswer}
            quotaRemaining={quotaData?.remaining}
          />
        </Panel>
      ) : null}

      {prefs.isVisible('index') ? (
        <Panel
          title="קונפיגורציית אינדקס"
          subtitle="0 קריאות LLM"
          icon={Layers}
          {...panelProps('index')}
          loading={indexes.isPending}
          error={indexes.error?.message}
        >
          <ProcessExplainer id="rag-index" {...RAG_EXPLAINERS.index} />
          <IndexConfigPanel
            indexes={indexes.data?.indexes ?? []}
            activeIndexId={indexId}
            onSelectIndex={(value) => setParam({ index: value })}
            selectedDocs={effectiveDocs}
            chunkSize={chunkSize}
            overlap={overlap}
            embeddingModel={embeddingModel}
            onChunkSizeChange={setChunkSize}
            onOverlapChange={setOverlap}
            onEmbeddingModelChange={setEmbeddingModel}
            k={k}
            retriever={retriever}
            denseWeight={denseWeight}
            onHitRateResult={setLiveHitRate}
          />
        </Panel>
      ) : null}

      {prefs.isVisible('corpus') ? (
        <Panel
          title="הקורפוס"
          subtitle="Task 1"
          icon={Database}
          {...panelProps('corpus')}
          loading={corpus.isPending}
          error={corpus.error?.message}
        >
          <ProcessExplainer id="rag-corpus" {...RAG_EXPLAINERS.corpus} />
          <CorpusPanel
            data={corpus.data}
            selectedDocs={effectiveDocs}
            onToggleDoc={(name) =>
              setSelectedDocs((current) => {
                const base = current ?? allDocNames;
                return base.includes(name) ? base.filter((n) => n !== name) : [...base, name];
              })
            }
          />
        </Panel>
      ) : null}

      {prefs.isVisible('chunks') ? (
        <Panel
          title="דפדפן צ'אנקים"
          subtitle="Task 3 — לקרוא לפני שמסיקים"
          icon={FileSearch}
          {...panelProps('chunks')}
        >
          <ProcessExplainer id="rag-chunks" {...RAG_EXPLAINERS.chunks} />
          <ChunkBrowserPanel indexId={indexId} documents={corpus.data?.documents ?? []} />
        </Panel>
      ) : null}

      {prefs.isVisible('evalset') ? (
        <Panel
          title="מערך ההערכה"
          subtitle="Task 2"
          icon={ListChecks}
          {...panelProps('evalset')}
          loading={evalSet.isPending}
          error={evalSet.error?.message}
        >
          <ProcessExplainer id="rag-evalset" {...RAG_EXPLAINERS.evalset} />
          <EvalSetPanel data={evalSet.data} onUseQuestion={useEvalQuestion} />
        </Panel>
      ) : null}

      {prefs.isVisible('baseline') ? (
        <Panel
          title="בייסליין ללא RAG"
          subtitle="Task 1"
          icon={BookOpen}
          {...panelProps('baseline')}
          loading={baseline.isPending}
          error={baseline.error?.message}
        >
          <ProcessExplainer id="rag-baseline" {...RAG_EXPLAINERS.baseline} />
          <BaselinePanel data={baseline.data} />
        </Panel>
      ) : null}

      {prefs.isVisible('metrics') ? (
        <Panel
          title="מדדי Task 5 — RAG מול בייסליין"
          icon={Gauge}
          {...panelProps('metrics')}
          loading={metrics.isPending}
          error={metrics.error?.message}
        >
          <ProcessExplainer id="rag-metrics" {...RAG_EXPLAINERS.metrics} />
          <MetricsPanel data={metrics.data} />
        </Panel>
      ) : null}

      {prefs.isVisible('perquestion') ? (
        <Panel
          title="פירוט לפי שאלה"
          subtitle="Task 5"
          icon={Microscope}
          {...panelProps('perquestion')}
          loading={perQuestion.isPending}
          error={perQuestion.error?.message}
        >
          <ProcessExplainer id="rag-perquestion" {...RAG_EXPLAINERS.perquestion} />
          <PerQuestionPanel data={perQuestion.data} />
        </Panel>
      ) : null}

      {prefs.isVisible('sweeps') ? (
        <Panel
          title="Task 6 — sweeps"
          subtitle="0 קריאות LLM"
          icon={BarChart3}
          {...panelProps('sweeps')}
          loading={sweeps.isPending}
          error={sweeps.error?.message}
        >
          <ProcessExplainer id="rag-sweeps" {...RAG_EXPLAINERS.sweeps} />
          <SweepsPanel data={sweeps.data} liveResult={liveHitRate} />
        </Panel>
      ) : null}

      {prefs.isVisible('experiments') ? (
        <Panel
          title="Task 6 — ניסויים"
          icon={FlaskConical}
          {...panelProps('experiments')}
          loading={experiments.isPending}
          error={experiments.error?.message}
        >
          <ProcessExplainer id="rag-experiments" {...RAG_EXPLAINERS.experiments} />
          <ExperimentsPanel data={experiments.data} />
        </Panel>
      ) : null}

      {prefs.isVisible('analysis') ? (
        <Panel
          title="ניתוח (א)/(ב)/(ג)"
          subtitle="Task 5"
          icon={Microscope}
          {...panelProps('analysis')}
          loading={analysis.isPending}
          error={analysis.error?.message}
        >
          <ProcessExplainer id="rag-analysis" {...RAG_EXPLAINERS.analysis} />
          <AnalysisPanel data={analysis.data} />
        </Panel>
      ) : null}
    </div>
  );
}
