// Which AI writes the answers -- api/agents/base.py dispatches by model name
// prefix (claude- => Anthropic, gemini- => Gemini), so any of these strings
// just flows through as TestRunRequest.model.
export const WRITER_MODEL_OPTIONS = [
  { value: 'gemini-flash-lite-latest', label: 'Gemini (חינם)' },
  { value: 'claude-haiku-4-5', label: 'Claude Haiku (בתשלום)' },
];

// Which AI judges the answers. Deliberately a different Gemini checkpoint
// than the writer's (not the same "gemini-flash-lite-latest") -- a judge
// sharing the exact writer checkpoint risks self-preference bias; see
// .claude/rules/hosted-llm-quota.md's 2026-08-13 CODIFY entry.
export const JUDGE_MODEL_OPTIONS = [
  { value: 'gemini-3.1-flash-lite', label: 'Gemini (חינם)' },
  { value: 'claude-haiku-4-5', label: 'Claude Haiku (בתשלום)' },
];
