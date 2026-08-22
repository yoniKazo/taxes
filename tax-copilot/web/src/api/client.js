const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const DEFAULT_TIMEOUT_MS = 30_000;
const LLM_TIMEOUT_MS = 180_000;    // a judged row is 4 throttled calls
const CORPUS_TIMEOUT_MS = 120_000; // parsing the PDF corpus, before any embedding

/**
 * Low-level fetch wrapper: builds the URL, sends JSON, and turns a non-2xx
 * response into a thrown Error whose message is the Hebrew `detail` string
 * produced by FastAPI's InvalidInputError handler (falls back to statusText).
 */
async function request(path, { method = 'GET', body, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  // Without a timeout a stalled request leaves the UI spinning with no way back.
  // Generation and judging legitimately take tens of seconds (src/llm.py enforces
  // a 4.2s floor between calls), so those callers raise the ceiling rather than
  // the default being as long as the slowest thing in the app.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error(`הבקשה חרגה מזמן ההמתנה (${Math.round(timeoutMs / 1000)} שניות).`);
    }
    throw new Error('לא הצלחתי להגיע לשרת. ודא ש-uvicorn רץ על פורט 8000.');
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errorBody = await response.json();
      if (errorBody && typeof errorBody.detail === 'string') {
        detail = errorBody.detail;
      }
    } catch {
      // response body wasn't JSON — keep statusText
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return null;
  }
  return response.json();
}

// --- מחשבון ---

export function calculateTax(payload) {
  return request('/calculate', { method: 'POST', body: payload });
}

// --- Test Lab ---

export function listAgents() {
  return request('/agents');
}

export function getActiveRubric() {
  return request('/rubrics/active');
}

export function updateRubric(payload) {
  return request('/rubrics/active', { method: 'PUT', body: payload });
}

export function listTestQuestions(datasetName = 'tax_qa_v1') {
  return request(`/test-questions?dataset=${encodeURIComponent(datasetName)}`);
}

export function addTestQuestion(payload) {
  return request('/test-questions', { method: 'POST', body: payload });
}

export function deleteTestQuestion(id) {
  return request(`/test-questions/${id}`, { method: 'DELETE' });
}

export function listTestRuns() {
  return request('/test-runs');
}

export function createTestRun(payload) {
  return request('/test-runs', { method: 'POST', body: payload });
}

export function getTestRun(id) {
  return request(`/test-runs/${id}`);
}

export function submitRating(llmCallId, payload) {
  return request(`/llm-calls/${llmCallId}/ratings`, { method: 'POST', body: payload });
}

export function runJudge(testRunId) {
  return request(`/test-runs/${testRunId}/judge`, { method: 'POST' });
}

// Job-based variants: same work, but pollable and cancellable. A run is one
// throttled call per question and judging is four per answered row, so the
// blocking versions leave the UI silent for minutes.
export function createTestRunAsync(payload) {
  return request('/test-runs/async', { method: 'POST', body: payload });
}

export function runJudgeAsync(testRunId) {
  return request(`/test-runs/${testRunId}/judge/async`, { method: 'POST' });
}

export function getAgreement(testRunId) {
  return request(`/test-runs/${testRunId}/agreement`);
}

// --- RAG (מטלה 3) ---
//
// Everything here except answerWithRag/judgeRagAnswer costs zero LLM calls --
// it is served from the assignment's result files or from a local embedding
// model. The two that do cost are named so at their call sites.

export function getRagCorpus() {
  return request('/rag/corpus', { timeoutMs: CORPUS_TIMEOUT_MS });
}

export function getRagEvalSet() {
  return request('/rag/eval-set');
}

export function getRagBaseline() {
  return request('/rag/baseline');
}

export function getRagMetrics() {
  return request('/rag/metrics');
}

export function getRagPerQuestion() {
  return request('/rag/per-question');
}

export function getRagAnalysis() {
  return request('/rag/analysis');
}

export function getRagSweeps() {
  return request('/rag/sweeps');
}

export function getRagExperiments() {
  return request('/rag/experiments');
}

export function getRagIndexes() {
  return request('/rag/indexes');
}

export function previewRagChunks(payload) {
  return request('/rag/indexes/preview', {
    method: 'POST', body: payload, timeoutMs: CORPUS_TIMEOUT_MS,
  });
}

export function buildRagIndex(payload) {
  return request('/rag/indexes/build', { method: 'POST', body: payload });
}

export function deleteRagIndex(indexId) {
  return request(`/rag/indexes/${encodeURIComponent(indexId)}`, { method: 'DELETE' });
}

export function browseRagChunks(params) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
  );
  return request(`/rag/chunks?${query}`, { timeoutMs: CORPUS_TIMEOUT_MS });
}

export function retrieveRagChunks(payload) {
  return request('/rag/retrieve', { method: 'POST', body: payload, timeoutMs: CORPUS_TIMEOUT_MS });
}

export function evaluateRagRetrieval(payload) {
  return request('/rag/evaluate-retrieval', { method: 'POST', body: payload });
}

// One job registry on the server, so one status endpoint for every job kind.
export function getRagJob(jobId) {
  return request(`/jobs/${jobId}`);
}

export function cancelRagJob(jobId) {
  return request(`/jobs/${jobId}/cancel`, { method: 'POST' });
}

export function getRagQuota() {
  return request('/rag/quota');
}

/** Costs 1 LLM call. */
export function answerWithRag(payload) {
  return request('/rag/answer', { method: 'POST', body: payload, timeoutMs: LLM_TIMEOUT_MS });
}

/** Costs 4 LLM calls (~20s at the throttle floor). */
export function judgeRagAnswer(payload) {
  return request('/rag/judge', { method: 'POST', body: payload, timeoutMs: LLM_TIMEOUT_MS });
}
