"""Task 5: score RAG and the baseline on the same eval set, head to head.

Retrieval metrics (hit-rate, context relevance) and generation metrics
(faithfulness, answer relevance, correctness) are kept apart on purpose: when a
score drops you need to know which half broke.

The baseline gets only answer relevance and correctness -- it retrieved nothing,
so context relevance and faithfulness are undefined for it rather than zero.
"""

import os
import sys

import pandas as pd

from assignment3_build_eval_set import load_eval_set
from assignment3_run_rag import load_rag_results
from judges import (JUDGE_VERSION, VERDICT_SCORE, judge_answer_relevance,
                    judge_context_relevance, judge_correctness, judge_faithfulness,
                    refusal_correctness)
from llm import throttle
from retrieval_eval import hit_rate_row

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSIGNMENT_DIR = os.path.join(SCRIPT_DIR, "..", "assignment3")
BASELINE_PATH = os.path.join(ASSIGNMENT_DIR, "data", "baseline_results.csv")
OUTPUT_PATH = os.path.join(ASSIGNMENT_DIR, "assignment_03.xlsx")

JUDGE_COLUMNS = ["context_relevance", "faithfulness", "answer_relevance", "correctness"]


def reclassify_baseline(row: pd.Series) -> str:
    """The assignment asks for refused / correct / hallucinated.

    assignment3_baseline.py collapses every non-`good` verdict into
    "hallucinated", which overstates it: an `ok` verdict means the answer was
    directionally right but incomplete, not confidently wrong. Recomputed here
    from the correctness verdict Task 5 already produces, so it costs no extra
    calls, and `partial` is reported as its own bucket rather than hidden.
    """
    if row["baseline_classification"] == "refused":
        return "refused"
    return {"good": "correct", "ok": "partial", "bad": "hallucinated"}[row["baseline_correctness"]]


def judge_rag_row(row: pd.Series) -> dict:
    """Four judges, four deliberately narrow contexts.

    context relevance must not see the answer or it reasons backwards from it;
    faithfulness must not see the reference answer or it grades world-truth
    instead of grounding.

    judge_faithfulness is called WITHOUT `question` on purpose. That is the v1
    behaviour, which we now know mis-scores correct refusals -- but Task 5 and
    all three Task 6 experiments ran against it, and swapping the measuring
    instrument mid-experiment would make the deltas meaningless. The fixed judge
    is measured separately in assignment3_judge_recalibration.py.
    """
    chunks = row["retrieved_texts"]
    out = {}
    for name, verdict in [
        ("context_relevance", judge_context_relevance(row["question"], chunks)),
        ("faithfulness", judge_faithfulness(row["rag_answer"], chunks)),
        ("answer_relevance", judge_answer_relevance(row["question"], row["rag_answer"])),
        ("correctness", judge_correctness(row["question"], row["rag_answer"], row["reference_answer"])),
    ]:
        out[f"rag_{name}"] = verdict.verdict
        out[f"rag_{name}_explanation"] = verdict.explanation
    out["judge_version"] = JUDGE_VERSION
    return out


def judge_baseline_row(row: pd.Series) -> dict:
    out = {}
    for name, verdict in [
        ("answer_relevance", judge_answer_relevance(row["question"], row["baseline_answer"])),
        ("correctness", judge_correctness(row["question"], row["baseline_answer"], row["reference_answer"])),
    ]:
        out[f"baseline_{name}"] = verdict.verdict
        out[f"baseline_{name}_explanation"] = verdict.explanation
    out["baseline_context_relevance"] = "N/A"
    out["baseline_faithfulness"] = "N/A"
    out["judge_version"] = JUDGE_VERSION
    return out


def build_dataframe() -> pd.DataFrame:
    eval_set = load_eval_set()
    baseline = pd.read_csv(BASELINE_PATH, encoding="utf-8-sig")
    rag = pd.DataFrame(load_rag_results())
    df = eval_set.merge(baseline, on="id").merge(rag, on="id")

    scored = []
    for i, (_, row) in enumerate(df.iterrows()):
        print(f"[{i + 1}/{len(df)}] id={row['id']} ({row['category']})")
        hit = hit_rate_row(row["evidence_doc"], row["evidence_page"],
                           row["retrieved_docs"], row["retrieved_locations"])
        throttle(i)
        judged = {**judge_rag_row(row), **judge_baseline_row(row)}
        scored.append({
            **hit,
            **judged,
            "rag_refusal_correctness": refusal_correctness(row["answerable"], row["rag_answered"]),
            "baseline_refusal_correctness": refusal_correctness(
                row["answerable"], row["baseline_classification"] != "refused"),
        })

    df = pd.concat([df.reset_index(drop=True), pd.DataFrame(scored)], axis=1)
    df["baseline_classification"] = df.apply(reclassify_baseline, axis=1)
    return df


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    """One table: baseline vs RAG, per metric, split easy/hard."""
    rows = []
    for difficulty in ["easy", "hard", "ALL"]:
        slice_df = df if difficulty == "ALL" else df[df["difficulty"] == difficulty]
        answerable = slice_df[slice_df["answerable"]]
        record = {"slice": difficulty, "n": len(slice_df), "n_answerable": len(answerable)}
        record["rag_hit_at_k"] = answerable["hit_at_k"].mean()
        record["rag_hit_at_k_any_doc"] = answerable["hit_at_k_any_doc"].mean()
        for metric in JUDGE_COLUMNS:
            record[f"rag_{metric}"] = slice_df[f"rag_{metric}"].map(VERDICT_SCORE).mean()
        for metric in ["answer_relevance", "correctness"]:
            record[f"baseline_{metric}"] = slice_df[f"baseline_{metric}"].map(VERDICT_SCORE).mean()
        record["rag_false_answers"] = (slice_df["rag_refusal_correctness"] == "false_answer").sum()
        record["rag_false_refusals"] = (slice_df["rag_refusal_correctness"] == "false_refusal").sum()
        record["baseline_false_answers"] = (slice_df["baseline_refusal_correctness"] == "false_answer").sum()
        record["baseline_false_refusals"] = (slice_df["baseline_refusal_correctness"] == "false_refusal").sum()
        for bucket in ["refused", "correct", "partial", "hallucinated"]:
            record[f"baseline_{bucket}"] = (slice_df["baseline_classification"] == bucket).sum()
        record["rag_latency_ms"] = slice_df["latency_ms"].mean()
        record["baseline_latency_ms"] = slice_df["baseline_latency_ms"].mean()
        record["rag_input_tokens"] = slice_df["input_tokens"].mean()
        record["baseline_input_tokens"] = slice_df["baseline_input_tokens"].mean()
        record["rag_output_tokens"] = slice_df["output_tokens"].mean()
        record["baseline_output_tokens"] = slice_df["baseline_output_tokens"].mean()
        rows.append(record)
    return pd.DataFrame(rows).round(3)


def mean_judge_score(df: pd.DataFrame) -> pd.Series:
    return sum(df[f"rag_{m}"].map(VERDICT_SCORE) for m in JUDGE_COLUMNS) / len(JUDGE_COLUMNS)


def find_rag_worse_than_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """(a) RAG is not a free upgrade -- find where retrieval dragged it down."""
    return df[(df["baseline_correctness"] == "good") & (df["rag_correctness"] != "good")]


def find_right_answer_broken_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """(b) correct answer, failed retrieval: the model already knew, and
    correctness alone would never have revealed it."""
    return df[(df["rag_correctness"] == "good") & (df["hit_at_k"] == False)]  # noqa: E712


def worst_rag_rows(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    return df.assign(mean_judge=mean_judge_score(df)).nsmallest(n, "mean_judge")


def to_excel(df: pd.DataFrame, summary: pd.DataFrame) -> None:
    export = df.copy()
    for col in ["rag_sources", "rag_evidence", "retrieved_docs", "retrieved_locations",
                "retrieved_texts", "hallucinated_citations"]:
        export[col] = export[col].map(lambda v: " | ".join(map(str, v)) if isinstance(v, list) else v)
    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
        export.to_excel(writer, sheet_name="per_question", index=False)
        summary.to_excel(writer, sheet_name="summary_table", index=False)


def load_scored(path: str = OUTPUT_PATH) -> pd.DataFrame:
    """Re-read the judged results so the summary and the (a)/(b)/(c) analysis can
    be recomputed without paying for 204 judge calls again."""
    df = pd.read_excel(path, sheet_name="per_question")
    df["retrieved_docs"] = df["retrieved_docs"].fillna("").str.split(" | ", regex=False)
    df["retrieved_texts"] = df["retrieved_texts"].fillna("").str.split(" | ", regex=False)
    df["hit_at_k"] = df["hit_at_k"].astype("boolean")
    return df


if __name__ == "__main__":
    if "--resummarise" in sys.argv:
        df = load_scored()
        df["baseline_classification"] = df.apply(reclassify_baseline, axis=1)
    else:
        df = build_dataframe()
    summary = summarise(df)
    to_excel(df, summary)
    print(f"\n{OUTPUT_PATH}\n")
    print(summary.to_string(index=False))
