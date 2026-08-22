# Plan Mode artifacts — S1

Both plans below were written and saved in Plan Mode **before** commit `39692df` ("Assignment 3: RAG over Israeli tax corpus + RAG Lab UI + docs", 2026-08-22 23:03) — the largest single change on this branch's history: 122 files, 15,398 insertions, versus 5,534 for the next-largest (the browser client) and 135 for the code-review fix commit. `2026-08-18-assignment3-rag.md` covers the RAG pipeline itself; `2026-08-20-rag-lab-ui.md` covers exposing it in the browser client.

The point of S1 isn't that a plan file exists — it's being able to point at something rejected or corrected before a line of code was written. Two examples, both quoted directly from the saved plans:

## 1. Rejected: writing to the canonical index from the UI

From `2026-08-20-rag-lab-ui.md`:

> אינדקס מותאם שנבנה מה-UI נשמר ב-`assignment3/index_custom/<slug>/`, **לעולם לא** ב-`assignment3/index/` (הקנוני, שכל הסקריפטים תלויים בו).

The UI needed a way to let a user build a custom index (different chunk size, different embedding model) — the obvious place to save it would have been the same path the assignment-3 scripts already load from. That was rejected before implementation: the canonical index is graded, submitted work, and a UI-triggered rebuild would have silently forked it out from under the scripts that depend on it. Custom indexes go to a separate, gitignored path instead.

## 2. Rejected: running the full evaluation suite from the UI

From `2026-08-20-rag-lab-ui.md`:

> **אסור** להריץ את כל מערך ההערכה מה-UI (~200 קריאות; המכסה היומית של 500 כבר נשרפה — [phaseb_run.log](../assignment3/data/phaseb_run.log)).

A natural UI feature — "re-run the whole eval set from the browser" — was rejected outright before it was built, because the daily 500-call Gemini quota had already been exhausted once mid-run during Task 6 phase B. The UI only exposes single-question and single-row operations (0, 1, or 4 calls); the full sweep stays a CLI-only script, run deliberately and rarely.
