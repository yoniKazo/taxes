const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Low-level fetch wrapper: builds the URL, sends JSON, and turns a non-2xx
 * response into a thrown Error whose message is the Hebrew `detail` string
 * produced by FastAPI's InvalidInputError handler (falls back to statusText).
 */
async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

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

export function getAgreement(testRunId) {
  return request(`/test-runs/${testRunId}/agreement`);
}
