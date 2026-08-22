"""Serving the finished assignment-3 artifacts. Zero LLM calls, zero recompute.

Everything here already exists on disk under assignment3/. The loaders and the
analysis finders are imported from the assignment scripts rather than
reimplemented -- if the write-up and the UI ever disagree about a number that is
a bug, and sharing the function is what makes it impossible.
"""

import json
import os

import pandas as pd

from api.rag import SRC_DIR  # noqa: F401  -- puts src/ on sys.path

import assignment3_evaluate as evaluate
import assignment3_experiments as experiments
from assignment3_build_eval_set import load_eval_set

ASSIGNMENT_DIR = os.path.abspath(os.path.join(SRC_DIR, "..", "assignment3"))
DATA_DIR = os.path.join(ASSIGNMENT_DIR, "data")
REPO_ROOT = os.path.abspath(os.path.join(SRC_DIR, "..", ".."))

# The four hard-question categories Task 2 requires, with the count each needs.
REQUIRED_CATEGORIES = {"multi-hop": 2, "unanswerable": 2, "negation": 1, "identifier": 1}


def _nan_to_none(value):
    """pandas NaN is not JSON-serialisable and reads as 0 in the UI."""
    if isinstance(value, float) and pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def _records(df: pd.DataFrame) -> list[dict]:
    return [{k: _nan_to_none(v) for k, v in row.items()} for row in df.to_dict("records")]


# --- Task 1: corpus ---------------------------------------------------------


def corpus() -> dict:
    """The manifest plus a per-document chunk count at the baseline settings."""
    from api.rag.retrieval import baseline_chunk_counts

    manifest = experiments.load_manifest()
    counts = baseline_chunk_counts()
    docs = [
        {
            **entry,
            "chunk_count": counts.get(entry["doc_name"], 0),
            "exists": os.path.exists(os.path.join(REPO_ROOT, entry["path"])),
        }
        for entry in manifest
    ]
    return {
        "documents": docs,
        "total_chunks": sum(counts.values()),
        "formats": sorted({d["format"] for d in docs}),
    }


# --- Task 2: eval set -------------------------------------------------------


def eval_set() -> dict:
    """The 34 questions, plus the coverage check the assignment spells out.

    Reported as measured state rather than as a claim in prose: a write-up can
    say "2 multi-hop"; this counts them.
    """
    df = load_eval_set()
    by_category = df["category"].value_counts().to_dict()
    coverage = [
        {
            "category": name,
            "required": required,
            "actual": int(by_category.get(name, 0)),
            "ok": int(by_category.get(name, 0)) >= required,
        }
        for name, required in REQUIRED_CATEGORIES.items()
    ]
    n_hard = int((df["difficulty"] == "hard").sum())
    return {
        "questions": _records(df),
        "n": len(df),
        "n_answerable": int(df["answerable"].sum()),
        "n_hard": n_hard,
        "by_category": {k: int(v) for k, v in by_category.items()},
        "by_difficulty": {k: int(v) for k, v in df["difficulty"].value_counts().items()},
        "coverage": coverage,
        # The assignment's own gates: 25-40 questions, 6+ hand-written hard ones.
        "size_ok": 25 <= len(df) <= 40,
        "hard_ok": n_hard >= 6,
    }


# --- Task 5 source: the judged spreadsheet ----------------------------------

_scored_cache: pd.DataFrame | None = None


def _scored() -> pd.DataFrame:
    """assignment_03.xlsx, re-split back into lists. Read once per process."""
    global _scored_cache
    if _scored_cache is None:
        df = evaluate.load_scored()
        df["baseline_classification"] = df.apply(evaluate.reclassify_baseline, axis=1)
        _scored_cache = df
    return _scored_cache


# --- Task 1: baseline -------------------------------------------------------


def baseline() -> dict:
    """The no-RAG run, bucketed refused / correct / partial / hallucinated.

    `partial` is a deliberate fourth bucket: assignment3_baseline.py collapsed
    every non-good verdict into "hallucinated", which overstates the
    hallucination rate. reclassify_baseline() recomputes it from the correctness
    verdict Task 5 already paid for.
    """
    scored = _scored()
    raw = pd.read_csv(os.path.join(DATA_DIR, "baseline_results.csv"), encoding="utf-8-sig")
    # The CSV carries the ORIGINAL classification, which collapsed every non-good
    # verdict into "hallucinated". Drop it so the merge cannot silently suffix
    # the two into _x/_y and leave the UI showing whichever it grabbed first.
    raw = raw.rename(columns={"baseline_classification": "baseline_classification_original"})
    merged = raw.merge(
        scored[
            [
                "id", "question", "baseline_classification", "baseline_correctness",
                "baseline_correctness_explanation", "difficulty", "category", "answerable",
            ]
        ],
        on="id",
    )
    buckets = merged["baseline_classification"].value_counts().to_dict()
    return {
        "rows": _records(merged),
        "buckets": {
            name: int(buckets.get(name, 0))
            for name in ["refused", "correct", "partial", "hallucinated"]
        },
        "n": len(merged),
    }


# --- Task 5: metrics, per-question, analysis --------------------------------


def metrics() -> dict:
    df = _scored()
    return {
        "summary": _records(evaluate.summarise(df)),
        "judge_columns": evaluate.JUDGE_COLUMNS,
        # Task 4 asks for this number explicitly: how often the deterministic
        # guard caught the model citing a chunk that was never supplied.
        "hallucinated_citation_rows": int(df["citation_flag"].sum()),
        "refusal_mismatch_rows": int(df["refusal_mismatch"].sum()),
        "n": len(df),
        # The hard slice is 6 questions: one row is 16.7 points. Surfaced so the
        # UI can label hard-slice deltas as direction, not evidence.
        "hard_slice_n": int((df["difficulty"] == "hard").sum()),
    }


def per_question() -> dict:
    df = _scored()
    return {"rows": _records(df), "n": len(df)}


def analysis() -> dict:
    """Task 5 (a), (b) and (c), via the same finders the write-up used."""
    df = _scored()
    worse = evaluate.find_rag_worse_than_baseline(df)
    broken = evaluate.find_right_answer_broken_pipeline(df)
    worst = evaluate.worst_rag_rows(df, n=5)
    columns = [
        "id", "question", "category", "difficulty", "mean_judge", "rag_answer",
        "hit_at_k", "rag_context_relevance", "rag_faithfulness",
        "rag_answer_relevance", "rag_correctness",
    ]
    return {
        "rag_worse_than_baseline": _records(worse),
        "right_answer_broken_pipeline": _records(broken),
        # Zero rows here is a finding, not an empty table: hit@k = 0.969 left
        # only one missed retrieval, and on that row the system refused instead
        # of answering from memory -- so the scenario had no chance to occur.
        "right_answer_broken_pipeline_is_empty": len(broken) == 0,
        "worst_rows": _records(worst[columns]),
    }


# --- Task 6: sweeps and experiments -----------------------------------------


def sweeps() -> dict:
    df = pd.read_csv(os.path.join(DATA_DIR, "task6_sweeps.csv"), encoding="utf-8-sig")
    return {
        "rows": _records(df),
        "axes": sorted(df["sweep"].unique().tolist()),
        "baseline_settings": {
            "top_k": "k=5",
            "chunk_size": "1000/150",
            "embedding_model": "intfloat/multilingual-e5-small",
        },
    }


def experiments_summary() -> dict:
    """Phase B, reported honestly.

    exp1 was judged for 6 of 34 rows before the run hit the 500/day cap, and
    exp3 never ran. Averaging 6 rows and presenting the result beside a complete
    baseline is the exact failure this assignment penalises, so each experiment
    carries a status and the UI shows "not completed" instead of a number.
    """
    total = len(load_eval_set())
    out = []
    for name, config in experiments.EXPERIMENTS.items():
        judged_path = os.path.join(DATA_DIR, f"{name}_judged.json")
        results_path = os.path.join(DATA_DIR, f"{name}_rag_results.json")
        judged_rows = 0
        if os.path.exists(judged_path):
            with open(judged_path, encoding="utf-8") as f:
                judged_rows = len(json.load(f))
        status = "complete" if judged_rows >= total else "partial" if judged_rows else "missing"
        out.append({
            "name": name,
            "hypothesis": config["hypothesis"],
            "changed": config["changed"],
            "k": config.get("k"),
            "status": status,
            "generation_complete": os.path.exists(results_path),
            "rows_judged": judged_rows,
            "rows_total": total,
            "metrics": _experiment_metrics(name) if status == "complete" else None,
        })
    return {"experiments": out, "baseline_metrics": _records(evaluate.summarise(_scored()))}


def _experiment_metrics(name: str) -> dict:
    from assignment3_run_rag import load_rag_results

    rows = load_rag_results(os.path.join(DATA_DIR, f"{name}_rag_results.json"))
    with open(os.path.join(DATA_DIR, f"{name}_judged.json"), encoding="utf-8") as f:
        judged = json.load(f)
    df = load_eval_set().merge(pd.DataFrame(rows), on="id")
    df = pd.concat([df.reset_index(drop=True), pd.DataFrame(judged)], axis=1)
    return {k: _nan_to_none(v) for k, v in experiments.experiment_metrics(df).items()}
