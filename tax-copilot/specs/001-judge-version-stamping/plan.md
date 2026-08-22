# Implementation Plan: Judge Version Stamping

**Branch**: `001-judge-version-stamping` | **Date**: 2026-08-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-judge-version-stamping/spec.md`

## Summary

Add a `JUDGE_VERSION` constant to `src/judges.py`, computed as a short hash of the four judge prompt strings, and stamp it onto every row `judge_rag_row`/`judge_baseline_row` produce in `src/assignment3_evaluate.py`. No existing behavior (prompts, scoring, saved files) changes.

## Technical Context

**Language/Version**: Python 3.12 (matches `.venv`)

**Primary Dependencies**: stdlib `hashlib` only — no new dependency

**Storage**: N/A (metadata added to in-memory dicts that already get written to `assignment_03.xlsx` / JSON by existing code, untouched by this feature)

**Testing**: pytest, matching `tests/` conventions

**Target Platform**: same as the rest of `src/` — CLI scripts run locally

**Project Type**: single Python package (`src/`)

**Constraints**: must not change any of the four prompt strings; must not touch the 34 already-saved result rows (CLAUDE.md Forbidden #5 — no swapping the measuring instrument mid-experiment)

**Scale/Scope**: one new constant, one new tiny helper function, a one-line addition in two call sites, one test file

## Constitution Check

*Gate: this project's constitution is `CLAUDE.md` (M1), not the unfilled `.specify/memory/constitution.md` template — `.specify`'s own template is generic scaffolding this project never populated, while `CLAUDE.md` is the real, populated set of rules this codebase already runs on.*

- **Conventions**: type hints on the new function; no long docstring beyond what's needed (`CLAUDE.md` § Conventions). ✅ satisfied by the design below.
- **Forbidden #5** ("never swap the measurement instrument mid-experiment and compare old numbers to new"): this feature adds metadata, not a metric change — the 34 saved rows are explicitly untouched (see spec.md Edge Cases and Out of scope). ✅ gate passes; re-checked after Phase 1 below, since this is the one rule this feature could most easily violate by accident.

No other gate in `CLAUDE.md` applies (no Gemini calls, no Hebrew-text handling, no new data file).

## Project Structure

### Documentation (this feature)

```text
specs/001-judge-version-stamping/
├── spec.md
├── plan.md      (this file)
└── tasks.md
```

### Source (this feature)

```text
src/
├── judges.py               # + _compute_judge_version(), + JUDGE_VERSION
└── assignment3_evaluate.py # judge_rag_row / judge_baseline_row: + out["judge_version"]
tests/
└── test_judge_version.py   # new
```

## Design

`_compute_judge_version(prompts: tuple[str, ...] = (CONTEXT_RELEVANCE_PROMPT, FAITHFULNESS_PROMPT, ANSWER_RELEVANCE_PROMPT, CORRECTNESS_PROMPT)) -> str` joins the four prompts with a separator, SHA-256s the result, and returns the first 8 hex characters. Taking `prompts` as a parameter (defaulted to the real module constants) rather than reading module globals directly is what makes FR-002/FR-003 testable without monkeypatching: a test can pass a different tuple and assert a different hash, proving the value actually depends on prompt content instead of being a hardcoded string that happens to look derived.

`JUDGE_VERSION = _compute_judge_version()` is computed once at import time, same lifecycle as `JUDGE_MODEL`.

Re-checking the Constitution gate after this design: still passes — the hash is read-only over existing constants, nothing about `_judge()` or the four prompts changes, and no saved file is written or re-read by this feature.

## Verification

- `pytest tests/test_judge_version.py` — new tests (see tasks.md).
- Full existing suite (`pytest`) still green — this feature only adds a key to a returned dict, so no existing assertion should reference `judge_version`'s absence in a way that breaks.
- Manual: import `judges`, print `JUDGE_VERSION`, confirm it's an 8-character hex string.
