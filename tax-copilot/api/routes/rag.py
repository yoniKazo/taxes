"""RAG lab endpoints (assignment 3), grouped by what they cost.

FREE -- no LLM calls, served from disk or from a local embedding model:
    GET  /rag/corpus              GET  /rag/eval-set        GET  /rag/baseline
    GET  /rag/metrics             GET  /rag/per-question    GET  /rag/analysis
    GET  /rag/sweeps              GET  /rag/experiments
    GET  /rag/indexes             POST /rag/indexes/preview
    POST /rag/indexes/build       DELETE /rag/indexes/{id}
    GET  /rag/chunks              POST /rag/retrieve
    POST /rag/evaluate-retrieval

Job progress for the two long-running routes above is polled from the shared
GET /jobs/{id} (api/routes/test_runs.py) -- api/jobs.py keeps one registry, so a
second per-feature status endpoint would just be another way to ask the same
question.

COSTS QUOTA -- Gemini free tier is 15/min and 500/day:
    POST /rag/answer   1 call     POST /rag/judge   4 calls
    GET  /rag/quota    0 calls (reports today's spend so the UI can warn first)

Deliberately absent: any route that runs the whole 34-question eval set. That is
~204 calls and would burn 40% of the daily cap in one click; it stays on the CLI
where it has checkpointing and resume.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from api import jobs
from api.rag import artifacts, generation, retrieval
from api.rag.retrieval import IndexNotFound, ReadOnlyIndex
from api.rag_schemas import (AnswerRequest, BuildIndexRequest, EvaluateRetrievalRequest,
                             JudgeRequest, PreviewRequest, RetrieveRequest)
from api.routes._common import get_db

router = APIRouter(prefix="/rag", tags=["rag"])


# --- Tasks 1-6: finished artifacts, straight off disk ------------------------


@router.get("/corpus")
def get_corpus() -> dict:
    return artifacts.corpus()


@router.get("/eval-set")
def get_eval_set() -> dict:
    return artifacts.eval_set()


@router.get("/baseline")
def get_baseline() -> dict:
    return artifacts.baseline()


@router.get("/metrics")
def get_metrics() -> dict:
    return artifacts.metrics()


@router.get("/per-question")
def get_per_question() -> dict:
    return artifacts.per_question()


@router.get("/analysis")
def get_analysis() -> dict:
    return artifacts.analysis()


@router.get("/sweeps")
def get_sweeps() -> dict:
    return artifacts.sweeps()


@router.get("/experiments")
def get_experiments() -> dict:
    return artifacts.experiments_summary()


# --- indexes ----------------------------------------------------------------


@router.get("/indexes")
def get_indexes() -> dict:
    return {"indexes": retrieval.list_indexes(),
            "embedding_models": retrieval.EMBEDDING_MODELS}


@router.post("/indexes/preview")
def post_preview(payload: PreviewRequest) -> dict:
    """Chunk count and boundaries with no embedding -- instant, so the user can
    see the cost of a chunk-size change before paying for a rebuild."""
    try:
        return retrieval.preview_chunks(
            payload.doc_names, payload.chunk_size, payload.chunk_overlap
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/indexes/build")
def post_build_index(payload: BuildIndexRequest) -> dict:
    """Minutes of CPU, so it returns a job id rather than blocking the request."""
    def work(report, should_cancel):
        return retrieval.build_index_with_progress(
            payload.doc_names, payload.chunk_size, payload.chunk_overlap,
            payload.embedding_model, report=report, should_cancel=should_cancel,
        )

    return jobs.submit("build_index", work).to_dict()


@router.delete("/indexes/{index_id}", status_code=204)
def delete_index(index_id: str):
    try:
        retrieval.delete_index(index_id)
    except ReadOnlyIndex as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IndexNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return JSONResponse(status_code=204, content=None)


# --- retrieval --------------------------------------------------------------


@router.get("/chunks")
def get_chunks(
    index_id: str = retrieval.DEFAULT_INDEX_ID,
    doc_name: str | None = None,
    doc_format: str | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = Query(default=10, ge=1, le=100),
    seed: int | None = None,
) -> dict:
    """Task 3's "actually look at it" step. `seed` gives the random sample."""
    try:
        return retrieval.browse_chunks(
            index_id, doc_name, doc_format, search, offset, limit, seed
        )
    except IndexNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/retrieve")
def post_retrieve(payload: RetrieveRequest) -> dict:
    try:
        return retrieval.retrieve(
            payload.query, payload.k, payload.index_id,
            payload.retriever, payload.dense_weight,
        )
    except IndexNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/evaluate-retrieval")
def post_evaluate_retrieval(payload: EvaluateRetrievalRequest) -> dict:
    """hit-rate@K over the answerable eval questions -- 32 embeddings, no judge,
    no API calls. This is what lets a config change be judged before it is paid
    for, which is exactly what Task 6 sweeps against."""
    def work(report, should_cancel):
        return retrieval.evaluate_retrieval(
            payload.index_id, payload.k, payload.retriever, payload.dense_weight,
            report=report, should_cancel=should_cancel,
        )

    return jobs.submit("evaluate_retrieval", work).to_dict()


# --- costs quota ------------------------------------------------------------


@router.get("/quota")
def get_quota(conn=Depends(get_db)) -> dict:
    return generation.quota(conn)


@router.post("/answer")
def post_answer(payload: AnswerRequest, conn=Depends(get_db)) -> dict:
    """One generation call. Blocks for a few seconds -- src/llm.py enforces a
    4.2s floor between calls, which is what keeps the free tier from 429ing."""
    chunks = [c.model_dump() for c in payload.chunks] if payload.chunks is not None else None
    try:
        return generation.answer(
            conn, payload.query, payload.index_id, payload.k,
            chunks, payload.retriever, payload.dense_weight,
        )
    except IndexNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/judge")
def post_judge(payload: JudgeRequest, conn=Depends(get_db)) -> dict:
    """Four calls, ~20 seconds at the throttle floor."""
    return generation.judge(
        conn, payload.question, payload.answer, payload.chunks,
        payload.reference_answer, payload.answerable, payload.answered,
    )
