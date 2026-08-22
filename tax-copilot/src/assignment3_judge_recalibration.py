"""Measure the faithfulness judge against its own fixed version.

Task 5 and Task 6 both ran with the original faithfulness judge, which did not
see the question. Rather than change the instrument mid-experiment and lose
comparability, the fixed judge is run separately here and the disagreement is
reported as a result in its own right.

Costs one call per row (34), no re-generation.
"""

import os
import sys

import pandas as pd

from assignment3_evaluate import load_scored
from judges import VERDICT_SCORE, judge_faithfulness
from llm import throttle

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "assignment3", "data", "faithfulness_recalibration.csv")


def main() -> None:
    df = load_scored()
    rows = []
    for i, (_, row) in enumerate(df.iterrows()):
        throttle(i)
        fixed = judge_faithfulness(row["rag_answer"], row["retrieved_texts"], question=row["question"])
        rows.append({
            "id": row["id"], "category": row["category"], "difficulty": row["difficulty"],
            "answerable": row["answerable"],
            "faithfulness_v1": row["rag_faithfulness"],
            "faithfulness_v2": fixed.verdict,
            "v2_explanation": fixed.explanation,
        })
        print(f"[{i + 1}/{len(df)}] id={row['id']}: {row['rag_faithfulness']} -> {fixed.verdict}")

    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    changed = out[out["faithfulness_v1"] != out["faithfulness_v2"]]
    print(f"\nשינו פסיקה: {len(changed)}/{len(out)}")
    print(changed[["id", "category", "faithfulness_v1", "faithfulness_v2"]].to_string(index=False))
    for label, slice_df in [("ALL", out), ("hard", out[out["difficulty"] == "hard"]),
                            ("unanswerable", out[~out["answerable"]])]:
        v1 = slice_df["faithfulness_v1"].map(VERDICT_SCORE).mean()
        v2 = slice_df["faithfulness_v2"].map(VERDICT_SCORE).mean()
        print(f"{label:14s} faithfulness v1={v1:.3f}  v2={v2:.3f}  delta={v2 - v1:+.3f}")


if __name__ == "__main__":
    main()
