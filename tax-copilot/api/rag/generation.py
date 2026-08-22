"""Grounded answers and the four judges. This is the half that costs quota.

Kept apart from retrieval.py so the cost boundary is visible in the import graph
rather than in a comment: nothing here is reachable from a route documented as
free. src/llm.py enforces a 4.2s floor between calls inside call_text(), so
these handlers block for real time -- fine for a local single-user app, and the
reason the UI shows a spend warning before every button that lands here.

Free-tier ceilings that shape what the UI is allowed to offer:
  15 requests/minute, 500 requests/day (.claude/rules/hosted-llm-quota.md).
A single answer is 1 call; judging one row is 4. Judging the whole 34-question
eval set is ~204 and belongs on the CLI, not behind a button.
"""

import sqlite3
from typing import Any

from langchain_core.documents import Document

from api.rag import SRC_DIR  # noqa: F401  -- puts src/ on sys.path
from api.rag import retrieval
from api.routes._common import log_llm_call

ANSWER_COST = 1
JUDGE_COST = 4
DAILY_QUOTA = 500

RAG_AGENT_NAME = "rag"
RAG_JUDGE_AGENT_NAME = "rag_judge"
LLM_SOURCE = "rag"


def _to_documents(chunks: list[dict]) -> list[Document]:
    """Rebuild LangChain Documents from the chunk payloads the client sends back.

    The client returns the chunks it wants included, so the metadata round-trips
    through the browser. Only the fields format_context() and the citation
    labels actually read are restored.
    """
    return [
        Document(
            page_content=chunk["text"],
            metadata={
                "doc_name": chunk.get("doc_name"),
                "page": chunk.get("page"),
                "section": chunk.get("section"),
                "chunk_index": chunk.get("chunk_index"),
            },
        )
        for chunk in chunks
    ]


def answer(
    conn: sqlite3.Connection,
    query: str,
    index_id: str = retrieval.DEFAULT_INDEX_ID,
    k: int = 5,
    chunks: list[dict] | None = None,
    retriever: str = "dense",
    dense_weight: float = 0.5,
) -> dict:
    """One generation call.

    `chunks` is the manual-selection path: the caller has already retrieved,
    unticked some of them, and wants the answer grounded in exactly what is left.
    An empty selection is allowed on purpose -- a grounded system given no
    context must refuse, and being able to watch that happen is the whole point
    of letting the user take chunks away.
    """
    from llm import GENERATOR_MODEL
    from rag_pipeline import RAG_SYSTEM_PROMPT, answer_with_rag_instrumented

    if chunks is None:
        retrieved = retrieval.retrieve(query, k, index_id, retriever, dense_weight)
        selected = retrieved["chunks"]
    else:
        retrieved = None
        selected = chunks

    documents = _to_documents(selected)
    parsed, meta = answer_with_rag_instrumented(
        query, k=len(documents), vectorstore=None, chunks=documents
    )

    log_llm_call(
        conn,
        agent_name=RAG_AGENT_NAME,
        model=GENERATOR_MODEL,
        temperature=0.0,
        system_prompt=RAG_SYSTEM_PROMPT,
        question=query,
        response=parsed.answer,
        latency_ms=meta["latency_ms"],
        input_tokens=meta["input_tokens"],
        output_tokens=meta["output_tokens"],
        source=LLM_SOURCE,
    )

    return {
        "query": query,
        "answer": parsed.answer,
        "sources": parsed.sources,
        "evidence": parsed.evidence,
        "answered": parsed.answered,
        "chunks_used": len(documents),
        "retrieval": retrieved,
        "latency_ms": meta["latency_ms"],
        "input_tokens": meta["input_tokens"],
        "output_tokens": meta["output_tokens"],
        # Deterministic guards, zero extra calls: a citation numbered past the
        # chunks actually supplied, or answered=True alongside the refusal text.
        "hallucinated_citations": meta["hallucinated_citations"],
        "citation_flag": meta["citation_flag"],
        "refusal_mismatch": meta["refusal_mismatch"],
    }


def judge(
    conn: sqlite3.Connection,
    question: str,
    answer_text: str,
    chunk_texts: list[str],
    reference_answer: str | None = None,
    answerable: bool | None = None,
    answered: bool | None = None,
) -> dict:
    """Four judges, four deliberately narrow contexts. Four calls, ~20 seconds.

    Unlike assignment3_evaluate.judge_rag_row(), faithfulness is called WITH the
    question. That is the corrected instrument: without the question the judge
    cannot tell a correct refusal from an unsupported claim, and it graded both
    of Task 5's correct refusals as `bad`. The historical numbers were left on
    the old instrument so the Task 6 deltas stay comparable -- so a live verdict
    here can legitimately disagree with the stored one for the same row.

    Correctness is skipped when no reference answer exists: there is nothing to
    compare against, and inventing a verdict would be worse than omitting one.
    """
    from judges import (judge_answer_relevance, judge_context_relevance,
                        judge_correctness, judge_faithfulness, refusal_correctness)
    from llm import JUDGE_MODEL

    verdicts: dict[str, Any] = {}
    calls = [
        ("context_relevance", lambda: judge_context_relevance(question, chunk_texts)),
        ("faithfulness", lambda: judge_faithfulness(answer_text, chunk_texts, question)),
        ("answer_relevance", lambda: judge_answer_relevance(question, answer_text)),
    ]
    if reference_answer:
        calls.append(
            ("correctness", lambda: judge_correctness(question, answer_text, reference_answer))
        )

    for name, call in calls:
        verdict = call()
        verdicts[name] = {"verdict": verdict.verdict, "explanation": verdict.explanation}

    log_llm_call(
        conn,
        agent_name=RAG_JUDGE_AGENT_NAME,
        model=JUDGE_MODEL,
        temperature=0.0,
        system_prompt="4 שופטים: context relevance, faithfulness, answer relevance, correctness",
        question=question,
        response=str({k: v["verdict"] for k, v in verdicts.items()}),
        latency_ms=None,
        input_tokens=None,
        output_tokens=None,
        source=LLM_SOURCE,
    )

    return {
        "verdicts": verdicts,
        "n_calls": len(calls),
        # Free, code-only, and the one metric that catches a confident answer to
        # a question the corpus cannot support.
        "refusal_correctness": (
            refusal_correctness(answerable, answered)
            if answerable is not None and answered is not None else None
        ),
        "faithfulness_instrument": "fixed",
    }


def quota(conn: sqlite3.Connection) -> dict:
    """Today's spend, so the UI can warn before a button costs anything.

    Counts what this app logged; calls made from the CLI scripts never reach
    llm_calls, so this is a floor on real usage, not the provider's own count.
    """
    from api.routes._common import now_iso

    today = now_iso()[:10]
    rows = conn.execute(
        "SELECT source, COUNT(*) AS n FROM llm_calls WHERE created_at LIKE ? GROUP BY source",
        (f"{today}%",),
    ).fetchall()
    by_source = {row["source"]: row["n"] for row in rows}
    used = sum(by_source.values())
    return {
        "date": today,
        "used_today": used,
        "daily_limit": DAILY_QUOTA,
        "remaining": max(0, DAILY_QUOTA - used),
        "by_source": by_source,
        "answer_cost": ANSWER_COST,
        "judge_cost": JUDGE_COST,
    }
