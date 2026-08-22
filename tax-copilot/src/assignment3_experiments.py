"""Task 6: improvement cycles, one variable at a time.

Phase A sweeps hit-rate only. That costs zero LLM calls, isolates retrieval, and
is what decides which knobs are worth a full judged re-measurement -- so the
Phase B hypotheses are pre-registered against measured failures rather than
picked after seeing which one happened to look good.

Phase B re-measures every metric on the SAME eval set and reports deltas.
"""

import json
import os
import shutil
import sys
import tempfile

import pandas as pd
from langchain_classic.retrievers import EnsembleRetriever  # moved out of langchain core in v1
from langchain_community.retrievers import BM25Retriever

from assignment3_build_eval_set import load_eval_set
from build_index import build_and_save_index, build_chunks, load_index, split_documents, load_raw_documents, load_manifest, enrich_section_metadata
from embeddings import PrefixedEmbeddings, BGE_MODEL, E5_MODEL
from retrieval_eval import hit_rate_row

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "assignment3", "data")
SWEEPS_PATH = os.path.join(DATA_DIR, "task6_sweeps.csv")

BASELINE_K = 5


def chunks_for(chunk_size: int = 1000, chunk_overlap: int = 150):
    manifest = load_manifest()
    chunks = split_documents(load_raw_documents(manifest), chunk_size, chunk_overlap)
    enrich_section_metadata(chunks, manifest)
    return chunks


def hit_rate_over_eval(retrieve, k: int = BASELINE_K) -> dict:
    """retrieve(query, k) -> list[Document]. Zero LLM calls."""
    eval_set = load_eval_set()
    answerable = eval_set[eval_set["answerable"]]
    results = []
    for _, row in answerable.iterrows():
        chunks = retrieve(row["question"], k)
        results.append({
            "difficulty": row["difficulty"],
            **hit_rate_row(row["evidence_doc"], row["evidence_page"],
                           [c.metadata["doc_name"] for c in chunks]),
        })
    df = pd.DataFrame(results)
    return {
        "hit_at_k": df["hit_at_k"].mean(),
        "hit_at_k_any_doc": df["hit_at_k_any_doc"].mean(),
        "hit_at_k_easy": df[df["difficulty"] == "easy"]["hit_at_k"].mean(),
        "hit_at_k_hard": df[df["difficulty"] == "hard"]["hit_at_k"].mean(),
        "n": len(df),
    }


def _temp_index(chunks, embeddings):
    path = tempfile.mkdtemp(prefix="a3_sweep_")
    return build_and_save_index(chunks, embeddings, index_dir=path), path


def sweep_top_k(ks=(3, 5, 8, 10)) -> list[dict]:
    vectorstore = load_index()
    return [
        {"sweep": "top_k", "setting": f"k={k}",
         **hit_rate_over_eval(lambda q, _k, vs=vectorstore: vs.similarity_search(q, k=_k), k)}
        for k in ks
    ]


def sweep_chunk_size(configs=((500, 100), (1000, 150), (1500, 200))) -> list[dict]:
    rows = []
    for chunk_size, overlap in configs:
        chunks = chunks_for(chunk_size, overlap)
        vectorstore, path = _temp_index(chunks, PrefixedEmbeddings(E5_MODEL))
        try:
            rows.append({"sweep": "chunk_size", "setting": f"{chunk_size}/{overlap}",
                         "n_chunks": len(chunks),
                         **hit_rate_over_eval(lambda q, k, vs=vectorstore: vs.similarity_search(q, k=k))})
        finally:
            shutil.rmtree(path, ignore_errors=True)
    return rows


def sweep_embedding_model(models=(E5_MODEL, BGE_MODEL)) -> list[dict]:
    chunks = chunks_for()
    rows = []
    for model_name in models:
        vectorstore, path = _temp_index(chunks, PrefixedEmbeddings(model_name))
        try:
            rows.append({"sweep": "embedding_model", "setting": model_name,
                         **hit_rate_over_eval(lambda q, k, vs=vectorstore: vs.similarity_search(q, k=k))})
        finally:
            shutil.rmtree(path, ignore_errors=True)
    return rows


def build_hybrid_retriever(k: int = BASELINE_K, dense_weight: float = 0.5):
    chunks = chunks_for()
    bm25 = BM25Retriever.from_documents(chunks)
    bm25.k = k
    dense = load_index().as_retriever(search_kwargs={"k": k})
    return EnsembleRetriever(retrievers=[dense, bm25], weights=[dense_weight, 1 - dense_weight])


def sweep_hybrid_bm25(weights=(0.3, 0.5, 0.7)) -> list[dict]:
    rows = []
    for dense_weight in weights:
        retriever = build_hybrid_retriever(dense_weight=dense_weight)
        rows.append({"sweep": "hybrid_bm25", "setting": f"dense={dense_weight}",
                     **hit_rate_over_eval(lambda q, k, r=retriever: r.invoke(q)[:k])})
    return rows


def run_phase_a() -> pd.DataFrame:
    rows = []
    for name, fn in [("top_k", sweep_top_k), ("chunk_size", sweep_chunk_size),
                     ("embedding_model", sweep_embedding_model), ("hybrid_bm25", sweep_hybrid_bm25)]:
        print(f"\n=== sweep: {name} ===")
        for row in fn():
            rows.append(row)
            print(f"  {row['setting']:32s} hit@k={row['hit_at_k']:.3f}  "
                  f"easy={row['hit_at_k_easy']:.3f}  hard={row['hit_at_k_hard']:.3f}")
    df = pd.DataFrame(rows).round(3)
    df.to_csv(SWEEPS_PATH, index=False, encoding="utf-8-sig")
    print(f"\n{SWEEPS_PATH}")
    return df


# --- Phase B: full re-measurement, one variable changed per experiment ---------
#
# Each hypothesis is written against a failure actually observed in Task 5 or in
# the Phase A sweep above, and recorded here BEFORE the run. Where the sweep
# already hints at the answer, the open question is whether the judged metrics
# follow hit-rate -- retrieving the right chunk is necessary, not sufficient.

EXPERIMENTS = {
    "exp1_top_k_8": {
        "hypothesis": (
            "Task 5 הראה שהפרוסה הקשה נכשלת ב-hit@k (0.75) וב-context relevance (0.583), "
            "בעוד שהפרוסה הקלה מושלמת. ה-sweep מראה ש-k=8 מעלה hit@k ל-1.0 גם בקשות. "
            "צפוי: faithfulness ו-correctness בפרוסה הקשה ישתפרו. סיכון: 3 קטעים נוספים "
            "מכניסים רעש שיוריד context relevance ואולי faithfulness בפרוסה הקלה."
        ),
        "changed": "top-K: 5 -> 8",
        "k": 8,
    },
    "exp2_bge_embeddings": {
        "hypothesis": (
            "המטלה מקבעת bge-small-en-v1.5, שנפסל ב-Task 3 על סמך 3 שאילתות בלבד. "
            "ה-sweep על כל 32 השאלות מאשר hit@k=0.719 מול 0.969. הניסוי הזה מכמת את "
            "המחיר המלא בכל ארבעת מדדי השופט, כדי שההחלטה להחליף מודל תהיה מגובה במספרים "
            "ולא רק ב-hit-rate."
        ),
        "changed": "embedding model: multilingual-e5-small -> bge-small-en-v1.5",
        "k": 5,
        "embeddings": BGE_MODEL,
    },
    "exp3_hybrid_bm25": {
        "hypothesis": (
            "השערה שנרשמה לפני Task 5: שאלת ה-identifier (49א(א1)) תיכשל ב-dense retrieval "
            "כי embeddings לא שומרים טוקנים מדויקים, ו-BM25 יתקן זאת. Task 5 כבר הפריך את "
            "החלק הראשון — השאלה הצליחה. ה-sweep מראה ש-BM25 במשקל dense=0.3 כן מעלה את "
            "הפרוסה הקשה ל-1.0 אך מוריד את הקלה ל-0.929. השאלה הנבדקת: האם התמורה הזו "
            "משתלמת במדדי השופט, או שזו החלפה שקולה."
        ),
        "changed": "retrieval: dense only -> hybrid dense(0.3)+BM25(0.7)",
        "k": 5,
        "hybrid_dense_weight": 0.3,
    },
}


def run_full_experiment(name: str) -> pd.DataFrame:
    """Re-run generation AND all four judges on the same eval set."""
    import assignment3_run_rag
    from assignment3_evaluate import judge_rag_row
    from judges import refusal_correctness

    config = EXPERIMENTS[name]
    k = config["k"]
    retriever = None
    if "embeddings" in config:
        chunks = chunks_for()
        vectorstore, temp_path = _temp_index(chunks, PrefixedEmbeddings(config["embeddings"]))
    else:
        vectorstore, temp_path = load_index(), None
    if "hybrid_dense_weight" in config:
        retriever = build_hybrid_retriever(k=k, dense_weight=config["hybrid_dense_weight"])

    try:
        results_path = os.path.join(DATA_DIR, f"{name}_rag_results.json")
        if os.path.exists(results_path):
            # Generation is deterministic given the same retriever config and eval
            # set, so a completed run is reused rather than paid for twice.
            rows = assignment3_run_rag.load_rag_results(results_path)
            print(f"  (משתמש ביצירה קיימת: {len(rows)} שורות מ-{os.path.basename(results_path)})")
        else:
            rows = assignment3_run_rag.run(k=k, vectorstore=vectorstore, retriever=retriever,
                                           output_path=results_path)
    finally:
        if temp_path:
            shutil.rmtree(temp_path, ignore_errors=True)

    eval_set = load_eval_set()
    df = eval_set.merge(pd.DataFrame(rows), on="id")

    # Judging is the expensive half (4 calls/row). Checkpoint after every row so
    # an interrupted run resumes instead of paying for the whole thing again.
    scored_path = os.path.join(DATA_DIR, f"{name}_judged.json")
    scored = json.load(open(scored_path, encoding="utf-8")) if os.path.exists(scored_path) else []
    if scored:
        print(f"  (ממשיך משיפוט קיים: {len(scored)}/{len(df)} שורות)")

    for i, (_, row) in enumerate(df.iterrows()):
        if i < len(scored):
            continue
        print(f"  judging [{i + 1}/{len(df)}] id={row['id']}")
        scored.append({
            **hit_rate_row(row["evidence_doc"], row["evidence_page"], row["retrieved_docs"]),
            **judge_rag_row(row),
            "rag_refusal_correctness": refusal_correctness(row["answerable"], row["rag_answered"]),
        })
        with open(scored_path, "w", encoding="utf-8") as f:
            json.dump(scored, f, ensure_ascii=False)

    return pd.concat([df.reset_index(drop=True), pd.DataFrame(scored)], axis=1)


def experiment_metrics(df: pd.DataFrame) -> dict:
    from assignment3_evaluate import JUDGE_COLUMNS
    from judges import VERDICT_SCORE

    out = {}
    for label, slice_df in [("all", df), ("easy", df[df["difficulty"] == "easy"]),
                            ("hard", df[df["difficulty"] == "hard"])]:
        answerable = slice_df[slice_df["answerable"]]
        out[f"hit_at_k_{label}"] = answerable["hit_at_k"].mean()
        for metric in JUDGE_COLUMNS:
            out[f"{metric}_{label}"] = slice_df[f"rag_{metric}"].map(VERDICT_SCORE).mean()
    out["false_answers"] = (df["rag_refusal_correctness"] == "false_answer").sum()
    out["false_refusals"] = (df["rag_refusal_correctness"] == "false_refusal").sum()
    out["latency_ms"] = df["latency_ms"].mean()
    out["input_tokens"] = df["input_tokens"].mean()
    return out


def run_phase_b() -> None:
    from assignment3_evaluate import load_scored

    baseline_metrics = experiment_metrics(load_scored())
    frames, summary_rows = {}, [{"experiment": "task5_baseline (e5, k=5, dense)",
                                 "changed": "-", **baseline_metrics}]

    for name in EXPERIMENTS:
        print(f"\n{'=' * 70}\n{name}: {EXPERIMENTS[name]['changed']}\n{'=' * 70}")
        df = run_full_experiment(name)
        frames[name] = df
        summary_rows.append({"experiment": name, "changed": EXPERIMENTS[name]["changed"],
                             **experiment_metrics(df)})

    summary = pd.DataFrame(summary_rows).round(3)
    deltas = summary.copy()
    numeric = deltas.select_dtypes("number").columns
    deltas[numeric] = (deltas[numeric] - deltas.loc[0, numeric]).round(3)
    deltas.loc[0, "experiment"] = "task5_baseline (reference = 0)"

    log = pd.DataFrame([{"experiment": n, "hypothesis": c["hypothesis"], "changed": c["changed"]}
                        for n, c in EXPERIMENTS.items()])

    out_path = os.path.join(SCRIPT_DIR, "..", "assignment3", "assignment3_experiments.xlsx")
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        pd.read_csv(SWEEPS_PATH, encoding="utf-8-sig").to_excel(writer, sheet_name="sweeps", index=False)
        summary.to_excel(writer, sheet_name="absolute", index=False)
        deltas.to_excel(writer, sheet_name="delta_vs_task5", index=False)
        log.to_excel(writer, sheet_name="experiment_log", index=False)
        for name, df in frames.items():
            export = df.copy()
            for col in ["rag_sources", "rag_evidence", "retrieved_docs", "retrieved_locations",
                        "retrieved_texts", "hallucinated_citations"]:
                export[col] = export[col].map(lambda v: " | ".join(map(str, v)) if isinstance(v, list) else v)
            export.to_excel(writer, sheet_name=name[:31], index=False)

    print(f"\n{out_path}\n")
    print(deltas.to_string(index=False))


if __name__ == "__main__":
    if "--phase-b" in sys.argv:
        run_phase_b()
    else:
        run_phase_a()
