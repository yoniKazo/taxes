# Feature Specification: Judge Version Stamping

**Feature Branch**: `001-judge-version-stamping`

**Created**: 2026-08-23

**Status**: Draft

**Input**: User description: "Stamp every judged result row with which version of the judge prompts produced it, so that a future prompt fix doesn't silently make two result files incomparable."

## Why this feature exists

Two entries in `IMPLEMENTATION.md` / `CLAUDE.md` already describe the same gap from two different angles:

- **What I'd do differently next time**: *"כל קובץ תוצאה במטלה 3 שומר את הפלט אך לא את גרסת ה-prompt של השופט שהפיק אותו, ולכן השוואת שתי ריצות דורשת ארכיאולוגיה של חותמות זמן. שדה `judge_version` אחד היה הופך שעה של בילוש להשוואה בטוחה."*
- **Open questions**: `exp1_top_k_8_judged.json` was judged with the fixed `judges.py` (patched 2026-08-18 23:43); Task 5's own results were judged with the old one. The faithfulness delta between them isn't comparable, and the only reason anyone found out was cross-referencing file mtimes against a commit timestamp.

This is not a hypothetical risk. It already happened once, and nothing caught it mechanically.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare two result files without timestamp archaeology (Priority: P1)

A future run re-judges the eval set after a judge prompt has been edited (e.g. the faithfulness fix from CODIFY 2026-08-18). Someone wants to know whether a metric delta between the old and new result files reflects a real system change or just a different measuring instrument.

**Why this priority**: This is the entire point of the feature — it's the one scenario that already caused real confusion once (the `judge_version`-less comparison in the Open Questions section).

**Independent Test**: Judge the same row twice — once, edit a judge prompt string, judge again — and confirm the two output rows carry different `judge_version` values without touching anything else about how the row is produced.

**Acceptance Scenarios**:

1. **Given** a row is judged by `judge_rag_row` or `judge_baseline_row`, **When** the resulting dict is inspected, **Then** it contains a `judge_version` key.
2. **Given** the four judge prompt constants in `judges.py` are unchanged, **When** `judge_version` is computed twice (e.g. two separate process runs), **Then** both computations produce the identical value.
3. **Given** any one of the four judge prompt constants changes by even one character, **When** `judge_version` is recomputed, **Then** the value differs from before.

### Edge Cases

- What happens to the 34 already-saved result rows in `assignment3/data/*.json`? They keep whatever they have today — no `judge_version` key, i.e. implicitly "unknown/pre-versioning". This feature does not retroactively judge or re-stamp them (that would itself be "swapping the measuring instrument mid-experiment," CLAUDE.md Forbidden #5); it only stamps new judging output going forward.
- Does this change what any judge scores? No — this is metadata only. The four prompt strings, the `_judge()` call, and every verdict/explanation are byte-for-byte unchanged.

## Requirements *(mandatory)*

- **FR-001**: The system MUST expose a `judges.JUDGE_VERSION` value that is a deterministic function of the four judge prompt constants (`CONTEXT_RELEVANCE_PROMPT`, `FAITHFULNESS_PROMPT`, `ANSWER_RELEVANCE_PROMPT`, `CORRECTNESS_PROMPT`).
- **FR-002**: `judge_rag_row` and `judge_baseline_row` in `assignment3_evaluate.py` MUST include `judge_version` in their returned dict.
- **FR-003**: The system MUST NOT require a human to remember to bump a version number by hand — the value is derived mechanically from the prompt text itself, so editing a prompt and forgetting to version-bump is not a state that can occur.
- **FR-004**: Existing saved result files MUST NOT be modified or re-judged by this feature.

## Out of scope

- Re-judging or migrating any of the 34 already-saved eval rows.
- Versioning anything other than the four judge prompts (e.g. the generator prompt, the embedding model, the retriever configuration already have their own tracking — see `corpus_manifest.json` and the index `meta.json`).
- A UI surface for comparing two `judge_version`s against each other — this feature only makes the comparison *possible*, not automatic.
