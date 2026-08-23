# CLAUDE.md — api/

Context local to this subtree only; see the root `CLAUDE.md` for the rest of the project.

## Split by cost, not by topic

`api/rag/` has three files, and the split follows LLM spend, not subject matter:

- `artifacts.py` and `retrieval.py` — **0 Gemini calls.** Both are testable in `pytest` with no `GEMINI_API_KEY` and no network.
- `generation.py` — the only file that calls Gemini. Anything that burns quota goes here, not into the other two.

A new route or module belongs on whichever side of that line it actually sits on.

## Retrieval correctness (CODIFY 2026-08-20)

- **Never call `assignment3_experiments.build_hybrid_retriever` from `api/`.** It hardcodes `chunks_for()` (1000/150 chunking) and `load_index()` (the canonical index), so it silently returns results from a different corpus than whatever the UI has configured. Use `retrieval.hybrid_retriever`, which takes an explicit vectorstore instead.
- **FAISS `similarity_search_with_score` returns L2 distance, not similarity** — smaller is better. The vectors are normalized, so `cos = 1 - L2²/2` converts correctly. A progress bar wired to the raw score directly draws the best-matching chunk as the emptiest bar.
- **`EnsembleRetriever` (hybrid) reports no comparable score at all.** Surface `null`, not a made-up number.

## Lazy client, always

Any route that touches an LLM must stay importable with no `GEMINI_API_KEY` set. `llm.get_client()` is lazy for exactly this reason — building the OpenAI-compatible client at import time once took down uvicorn on missing-key startup and made the free half of the RAG pipeline (`artifacts.py`, `retrieval.py`) untestable by association. Don't move client construction back to module scope.

## Long-running work

`api/jobs.py` is the only place for operations that take more than a request-response cycle (index builds, hit@k sweeps, Test Lab runs, judging) — it's what provides progress reporting and cancellation. Don't spin up a long operation directly inside a route handler.
