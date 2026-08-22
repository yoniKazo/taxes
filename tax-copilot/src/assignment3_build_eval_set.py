"""Task 2 (assembly): merge the generated + hand-written halves into one eval set.

Kept separate from generation so re-running the merge is free and the two halves
stay independently editable (the synthetic half was human-reviewed after
generation; the hard half was written by hand against the source documents).
"""

import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "assignment3", "data")
SYNTHETIC_PATH = os.path.join(DATA_DIR, "synthetic_questions.csv")
HARD_PATH = os.path.join(DATA_DIR, "hard_questions.csv")
OUTPUT_PATH = os.path.join(DATA_DIR, "tax_rag_eval_set.csv")

COLUMNS = ["id", "question", "reference_answer", "evidence_doc", "evidence_page",
           "answerable", "difficulty", "category"]


def load_eval_set(path: str = OUTPUT_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["answerable"] = df["answerable"].astype(bool)
    df["evidence_doc"] = df["evidence_doc"].fillna("")
    df["evidence_page"] = df["evidence_page"].fillna("")
    return df


def main() -> None:
    synthetic = pd.read_csv(SYNTHETIC_PATH, encoding="utf-8-sig")
    hard = pd.read_csv(HARD_PATH, encoding="utf-8-sig")
    merged = pd.concat([hard, synthetic], ignore_index=True)
    merged.insert(0, "id", range(1, len(merged) + 1))
    merged = merged[COLUMNS]
    merged.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print(f"{len(merged)} שאלות -> {OUTPUT_PATH}")
    print(f"  difficulty: {merged['difficulty'].value_counts().to_dict()}")
    print(f"  category:   {merged['category'].value_counts().to_dict()}")
    print(f"  answerable: {merged['answerable'].value_counts().to_dict()}")
    assert 25 <= len(merged) <= 40, "the assignment requires 25-40 questions"
    assert (merged["category"] == "unanswerable").sum() == 2
    assert (merged["category"] == "multi-hop").sum() == 2
    assert (merged["difficulty"] == "hard").sum() >= 6
    print("\nכל בדיקות המבנה עברו.")


if __name__ == "__main__":
    main()
