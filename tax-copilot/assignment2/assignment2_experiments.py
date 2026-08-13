"""Task 4: improvement cycle. Re-runs the SAME 14 sampled questions from Task 3
through two single-change experiments, so results are directly comparable to the
baseline scores already recorded in assignment_02.xlsx.

Experiment 1 (prompt engineering, tried first per the assignment's guidance):
    Baseline answers repeat a canned greeting/sign-off ("שלום רב!" ... "נשמח
    לעזור בשאלות נוספות!") in most rows (observed in Task 3 -> Tone=ok on
    id 3/23/24), and one row used an editorializing adjective ("שיעור נעים",
    id 9 -> Fluency=ok). Hypothesis: an explicit ban on greetings/sign-offs and
    subjective adjectives removes filler sentences and stray editorializing
    without touching grounding or length behavior.

Experiment 2 (decoding parameter, independent of the prompt change):
    Same baseline prompt, but temperature=0 instead of the provider default.
    Hypothesis: lower temperature reduces the same stylistic flourishes
    (greetings, "nice rate"-style adjectives) as a side effect of more
    deterministic decoding -- testing whether the fix from experiment 1 could
    have been had "for free" via decoding params instead of prompt changes.
"""

import os
import sys
import time

import pandas as pd
from dotenv import load_dotenv

from assignment2_generate import SYSTEM_PROMPT, ask, load_document, load_questions

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "assignment2_experiments.xlsx")

# Same 14 ids scored by hand in Task 3 -- required so the delta is meaningful.
SAMPLE_IDS = [1, 3, 5, 7, 9, 11, 13, 16, 18, 20, 21, 22, 23, 24]

SYSTEM_PROMPT_NO_FILLER = SYSTEM_PROMPT + """
5. אל תפתח בברכה (למשל "שלום רב", "בשמחה", "הי") ואל תסיים במשפט סגירה גנרי (למשל "נשמח לעזור בשאלות נוספות"). התחל ישר בתשובה.
6. אל תשתמש בתארים שיווקיים/מחמיאים לעובדות יבשות (למשל "שיעור נעים", "הטבה מצוינת"). תאר את העובדה בניטרליות."""

EXPERIMENTS = [
    {
        "name": "exp1_no_filler_prompt",
        "what_changed": "system prompt: נוסף איסור מפורש על ברכת פתיחה/משפט סגירה גנרי ועל תארים שיווקיים (SYSTEM_PROMPT_NO_FILLER)",
        "hypothesis": "מסיר את הפילר שגרם ל-Tone=ok ב-id 3/23/24 ואת ה-Fluency=ok ב-id 9, בלי לפגוע ב-Grounding/Length",
        "system_prompt": SYSTEM_PROMPT_NO_FILLER,
        "temperature": None,
    },
    {
        "name": "exp2_temperature_0",
        "what_changed": "decoding param בלבד: temperature=0 (במקום ברירת המחדל של הספק), אותו system prompt כמו ה-baseline",
        "hypothesis": "דיקוד דטרמיניסטי יותר יצמצם את אותן תופעות סגנוניות (ברכות, תארים) כתופעת לוואי, בלי לשנות את הפרומפט",
        "system_prompt": SYSTEM_PROMPT,
        "temperature": 0,
    },
]


def run_experiment(document: str, questions: list[dict], exp: dict) -> pd.DataFrame:
    rows = []
    for i, q in enumerate(questions):
        print(f"[{exp['name']}] [{i + 1}/{len(questions)}] {q['question'][:50]}")
        if i > 0:
            time.sleep(4)  # free-tier quota: 15 requests/minute
        result = ask(document, q["question"], system_prompt=exp["system_prompt"], temperature=exp["temperature"])
        rows.append({**q, **result})

    df = pd.DataFrame(rows)
    for col in ["Fluency", "Grammar", "Tone", "Length", "Grounding", "Latency", "final_score"]:
        df[col] = ""
    return df


def main() -> None:
    document = load_document()
    all_questions = {q["id"]: q for q in load_questions()}
    questions = [all_questions[i] for i in SAMPLE_IDS]

    baseline_path = os.path.join(SCRIPT_DIR, "assignment_02.xlsx")
    baseline_df = pd.read_excel(baseline_path)
    baseline_df = baseline_df[baseline_df["id"].isin(SAMPLE_IDS)]

    with pd.ExcelWriter(OUTPUT_PATH) as writer:
        baseline_df.to_excel(writer, sheet_name="baseline", index=False)
        for exp in EXPERIMENTS:
            df = run_experiment(document, questions, exp)
            df.to_excel(writer, sheet_name=exp["name"], index=False)

        log_df = pd.DataFrame(EXPERIMENTS)[["name", "what_changed", "hypothesis"]]
        log_df.to_excel(writer, sheet_name="experiment_log", index=False)

    print(f"\nDone. Wrote baseline + {len(EXPERIMENTS)} experiment sheets to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
