# Tasks: Judge Version Stamping

**Input**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

**Tests before implementation** — matches this project's TDD default (`~/.claude/CLAUDE.md`: "TDD תמיד: בדיקה נכשלת ראשון → קוד מינימלי → refactor") and M5's "spec commit before implementation commit," extended one level further here to "test commit intent before implementation."

## T1 — [P1] Write the failing test (`tests/test_judge_version.py`)

- `test_judge_version_is_deterministic`: call `judges._compute_judge_version()` twice, assert equal.
- `test_judge_version_changes_with_prompt_text`: call `judges._compute_judge_version(("a", "b", "c", "d"))` and `judges._compute_judge_version(("a", "b", "c", "e"))`, assert the two results differ.
- `test_judge_version_is_short_hex`: assert `judges.JUDGE_VERSION` is an 8-character lowercase hex string (`re.fullmatch(r"[0-9a-f]{8}", ...)`).
- `test_judge_rag_row_includes_judge_version` / `test_judge_baseline_row_includes_judge_version`: call each function with `call_structured` mocked/monkeypatched to avoid real Gemini calls (matching how `tests/test_agents_unit.py` already mocks LLM calls in this repo), assert the returned dict has `judge_version == judges.JUDGE_VERSION`.

Run `pytest tests/test_judge_version.py` — all fail (module doesn't have `_compute_judge_version`/`JUDGE_VERSION` yet, call sites don't stamp anything).

## T2 — [P1] Implement `_compute_judge_version` + `JUDGE_VERSION` in `src/judges.py`

Per plan.md's Design section: `hashlib.sha256`, first 8 hex chars, `prompts` tuple defaulted to the four real prompt constants.

## T3 — [P1] Stamp `judge_version` in `assignment3_evaluate.py`

One line in `judge_rag_row` and one in `judge_baseline_row`: `out["judge_version"] = JUDGE_VERSION` (import added at the top, next to the existing `judges` imports).

## T4 — Verify

- `pytest tests/test_judge_version.py` — all pass.
- `pytest` (full suite) — still green, no regressions.
- Manual: `python -c "import sys; sys.path.insert(0,'src'); import judges; print(judges.JUDGE_VERSION)"` prints an 8-character hex string.
