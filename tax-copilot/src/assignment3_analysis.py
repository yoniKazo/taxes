"""Task 5, part 3: surface the three cases the assignment requires, with evidence.

These are candidate-finders, not conclusion-writers. Every diagnosis in the
write-up is made by reading the chunks this prints -- "I think the embedding
model struggled" is not an analysis; "here are the 5 chunks it returned, none
from the right document" is.

Costs zero LLM calls: it reads the judged spreadsheet Task 5 already produced.
"""

import sys

from assignment3_evaluate import (find_rag_worse_than_baseline,
                                  find_right_answer_broken_pipeline, load_scored,
                                  mean_judge_score, reclassify_baseline, worst_rag_rows)

sys.stdout.reconfigure(encoding="utf-8")

RULE = "=" * 78


def _print_row(row, show_chunks: bool = True, n_chunks: int = 5) -> None:
    print(f"\nid={row['id']} | {row['category']} | {row['difficulty']}")
    print(f"  שאלה:        {row['question']}")
    print(f"  ייחוס:       {str(row['reference_answer'])[:220]}")
    print(f"  baseline:    [{row['baseline_classification']}] {str(row['baseline_answer'])[:220]}")
    print(f"  RAG:         {str(row['rag_answer'])[:280]}")
    print(f"  hit@k={row['hit_at_k']}  ctx={row['rag_context_relevance']}  "
          f"faith={row['rag_faithfulness']}  rel={row['rag_answer_relevance']}  "
          f"corr={row['rag_correctness']}  (baseline corr={row['baseline_correctness']})")
    print(f"  צפוי:        {row['evidence_doc']} | {row['evidence_page']}")
    print(f"  אוחזר:       {row['retrieved_docs']}")
    if show_chunks:
        for i, chunk in enumerate(row["retrieved_texts"][:n_chunks], 1):
            print(f"    [{i}] {str(chunk)[:200]}")


def main() -> None:
    df = load_scored()
    df["baseline_classification"] = df.apply(reclassify_baseline, axis=1)

    print(f"{RULE}\n(a) שאלות שבהן RAG הרע לעומת הבייסליין\n{RULE}")
    worse = find_rag_worse_than_baseline(df)
    print(f"נמצאו {len(worse)}")
    for _, row in worse.iterrows():
        _print_row(row)

    print(f"\n\n{RULE}\n(b) תשובה נכונה, צינור שבור (correctness=good אך hit@k=False)\n{RULE}")
    broken = find_right_answer_broken_pipeline(df)
    print(f"נמצאו {len(broken)}")
    for _, row in broken.iterrows():
        _print_row(row)

    print(f"\n\n{RULE}\n(c) חמש התשובות הגרועות ביותר — retrieval או generation?\n{RULE}")
    worst = worst_rag_rows(df, 5)
    for _, row in worst.iterrows():
        verdict = "retrieval" if (row["hit_at_k"] is False or row["rag_context_relevance"] == "bad") else "generation"
        print(f"\n--- סיווג אוטומטי מוצע: {verdict} (mean judge={row['mean_judge']:.2f}) ---")
        _print_row(row)


if __name__ == "__main__":
    main()
