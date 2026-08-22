"""Task 1: the no-RAG baseline.

Asks the generator model every eval question with no documents at all, then
classifies each response as refused / correct / hallucinated. Without this,
"RAG works!" is an unfalsifiable claim -- and if the naive model already answers
most questions, the questions are testing world knowledge rather than the corpus.
"""

import os
import sys

import pandas as pd

from assignment3_build_eval_set import load_eval_set
from judges import judge_correctness
from llm import call_text, throttle

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "assignment3", "data", "baseline_results.csv")

REFUSAL_SENTENCE = "אינני יודע."

BASELINE_SYSTEM_PROMPT = f"""אתה יועץ מס שעונה על שאלות מיסוי בישראל לשנת המס 2026, מתוך הידע הכללי שלך בלבד.

כללים:
1. ענה רק אם אתה בטוח בתשובה. אל תנחש מספרים, שיעורים או סעיפי חוק.
2. אם אינך יודע בביטחון, השב **בדיוק** במשפט: "{REFUSAL_SENTENCE}" — בלי שום תוספת.
3. אם ענית — 1–4 משפטים ממוקדים."""


def ask_baseline(question: str) -> dict:
    result = call_text(BASELINE_SYSTEM_PROMPT, question)
    return {
        "baseline_answer": result.text,
        "baseline_latency_ms": result.latency_ms,
        "baseline_input_tokens": result.input_tokens,
        "baseline_output_tokens": result.output_tokens,
    }


def classify(answer: str, question: str, reference_answer: str) -> tuple[str, str]:
    """refused / correct / hallucinated -- reuses the shared correctness judge
    rather than defining a second, subtly different notion of 'right'."""
    if REFUSAL_SENTENCE in answer.strip():
        return "refused", "סירב לענות (זוהה בקוד, ללא שופט)"
    verdict = judge_correctness(question, answer, reference_answer)
    label = "correct" if verdict.verdict == "good" else "hallucinated"
    return label, verdict.explanation


def main() -> None:
    eval_set = load_eval_set()
    rows = []
    for i, (_, row) in enumerate(eval_set.iterrows()):
        print(f"[{i + 1}/{len(eval_set)}] id={row['id']} ({row['category']}) {row['question'][:55]}")
        throttle(i)
        result = ask_baseline(row["question"])
        throttle(1)
        label, explanation = classify(result["baseline_answer"], row["question"], row["reference_answer"])
        print(f"      -> {label}")
        rows.append({"id": row["id"], **result,
                     "baseline_classification": label,
                     "baseline_classification_explanation": explanation})

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n{len(df)} שורות -> {OUTPUT_PATH}")
    print(df["baseline_classification"].value_counts().to_string())


if __name__ == "__main__":
    main()
