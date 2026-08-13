"""Task 5+6: LLM-as-judge. Applies assignment2_rubric.md verbatim to score
Fluency/Grammar/Tone/Length/Grounding for every row in assignment_02.xlsx,
using a different model than generation (gemini-flash-latest vs.
gemini-flash-lite-latest) to reduce self-enhancement bias. Latency is never
sent to the judge -- its rating is derived programmatically from latency_ms,
same as the pass bar / go-no-go rules from Task 1.
"""

import json
import os
import re
import sys
import time

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError
from typing import Literal

from assignment2_generate import load_document, load_questions

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "assignment_02.xlsx")

JUDGE_MODEL = "gemini-3.1-flash-lite"  # different checkpoint than gemini-flash-lite-latest used in Task 2/4
# Note: non-"lite" tiers (gemini-flash-latest -> gemini-3.6-flash, gemini-3.5-flash) are capped
# at 20 free requests/day on this key -- too tight for a 24-row run. A pinned "-lite" checkpoint
# keeps the same generous free-tier quota as generation while still being a different model
# from the one used in Task 2/4. See assignment2_writeup.md for the full story.

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)

Verdict = Literal["good", "ok", "bad"]


class CriterionVerdict(BaseModel):
    explanation: str
    verdict: Verdict


class JudgeOutput(BaseModel):
    fluency: CriterionVerdict
    grammar: CriterionVerdict
    tone: CriterionVerdict
    length: CriterionVerdict
    grounding: CriterionVerdict


# Copied verbatim from assignment2_rubric.md ("1a. הגדרות דירוג") -- Latency is
# intentionally excluded, per the assignment: an LLM cannot know its own call's
# wall-clock time, so it is measured in code, never judged.
RUBRIC_TEXT = """
### Fluency (שטף)
good: התשובה קריאה כמשפט/משפטים טבעיים בעברית; אין ניסוח מוזר או מבנה שבור.
ok: 1–2 ניסוחים מגושמים או לא-אידיומטיים, אך המשמעות ברורה בקריאה ראשונה.
bad: 3+ ניסוחים מגושמים, או משפט שצריך לקרוא פעמיים כדי להבין, או ערבוב שפות/תווים לא תקין.

### Grammar (דקדוק)
good: אין שגיאות כתיב/פיסוק/התאמת מין-מספר.
ok: 1–2 שגיאות קטנות (כתיב/פיסוק) שלא פוגעות בהבנה.
bad: 3+ שגיאות, או שגיאה שמשנה את המשמעות.

### Tone (טון)
good: קול יועץ מס ידידותי, בטוח ומדויק — לא יבש-רובוטי ולא "משווק" מדי.
ok: הטון סביר אך שטוח/גנרי, בלי לפגוע במקצועיות.
bad: טון לא מתאים: מתנשא, מתחמק, אגרסיבי, disclaimer-heavy עד כדי חוסר שימושיות, או קופי-פייסט של קטע מהמסמך בלי ניסוח.

### Length (אורך, במשפטים)
good: 1–3 משפטים ממוקדים (או משפט קצר יחיד כשזו התשובה המלאה, כולל "לא מצאתי את זה במסמך").
ok: 4–5 משפטים, או משפט יחיד לא-שלם/קטוע.
bad: 6+ משפטים, או תשובה ריקה/מילה בודדת שאינה תשובה.

### Grounding (ביסוס במקור) -- הקריטריון הכי קריטי
good: כל טענה עובדתית בתשובה נתמכת ישירות במסמך המצורף, או שהתשובה מזהה נכון ששאלה היא מחוץ להיקף המסמך ("לא מצאתי את זה במסמך" / הפניה לכך שהמסמך עוסק בשכירים בלבד). ניסוחי "צבע" גנריים שאינם טענה עובדתית מותרים.
ok: טענה עובדתית אחת מנוסחת בצורה מקורבת/לא-מדויקת ביחס למסמך, אך אין טענה שהומצאה יש מאין ואין סתירה לעובדה מפורשת במסמך.
bad: לפחות טענה עובדתית אחת שאינה במסמך כלל, או סתירה לעובדה מפורשת במסמך, או תשובה עניינית לשאלה שמחוץ להיקף המסמך במקום לזהות שאין עליה מידע.
"""

JUDGE_SYSTEM_PROMPT = f"""אתה שופט איכות (LLM judge) שמעריך תשובות של בוט Q&A על מיסוי שכירים בישראל.
החל את הרוברייק הבאה *במדויק* כפי שהיא מנוסחת -- אל תשתמש בסטנדרטים משלך:
{RUBRIC_TEXT}

לכל אחד מ-5 הקריטריונים (fluency, grammar, tone, length, grounding) החזר `explanation` (הסבר קצר לפסיקה, בעברית) ולפני זה נמק במדויק לפי הרוברייק, ואז `verdict` (good/ok/bad).
לצורך grounding, המקור היחיד המותר הוא המסמך המצורף -- לא ידע עולם, לא מה שאתה "יודע" על מיסוי ישראלי.
החזר אך ורק JSON תקני בפורמט הבא, ללא טקסט נוסף, ללא code fences:
{{"fluency": {{"explanation": "...", "verdict": "good|ok|bad"}}, "grammar": {{...}}, "tone": {{...}}, "length": {{...}}, "grounding": {{...}}}}"""


def latency_rating(latency_ms: float) -> str:
    if latency_ms <= 2000:
        return "good"
    if latency_ms <= 5000:
        return "ok"
    return "bad"


def compute_final_score(ratings: dict) -> str:
    """Same pass bar / go-no-go rules as assignment2_rubric.md 1b."""
    if ratings["Grounding"] != "good":
        return "fail"
    if ratings["Length"] == "bad":
        return "fail"
    good_count = sum(1 for v in ratings.values() if v == "good")
    bad_count = sum(1 for v in ratings.values() if v == "bad")
    return "pass" if good_count >= 4 and bad_count == 0 else "fail"


def judge(document: str, question: str, answer: str) -> JudgeOutput:
    user_content = f"מסמך:\n{document}\n\nשאלה: {question}\n\nתשובת הבוט להערכה: {answer}"
    for attempt in range(5):
        try:
            response = client.chat.completions.create(
                model=JUDGE_MODEL,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
            return JudgeOutput.model_validate_json(raw)
        except RateLimitError:
            if attempt == 4:
                raise
            time.sleep(15)
        except (ValidationError, json.JSONDecodeError) as e:
            if attempt == 4:
                raise
            print(f"  (retry: malformed judge output: {e})")
            time.sleep(2)


def sanity_check(n: int = 5) -> None:
    document = load_document()
    df = pd.read_excel(OUTPUT_PATH)
    for _, row in df.head(n).iterrows():
        print(f"\n=== id={row['id']} ({row['category']}) ===")
        print(f"Q: {row['question']}")
        print(f"A: {row['generated_answer']}")
        result = judge(document, row["question"], row["generated_answer"])
        for name, cv in result.model_dump().items():
            print(f"  {name}: {cv['verdict']} -- {cv['explanation']}")
        time.sleep(4)


def full_run() -> pd.DataFrame:
    document = load_document()
    df = pd.read_excel(OUTPUT_PATH)

    judge_cols = [
        "judge_Fluency", "judge_Fluency_explanation",
        "judge_Grammar", "judge_Grammar_explanation",
        "judge_Tone", "judge_Tone_explanation",
        "judge_Length", "judge_Length_explanation",
        "judge_Grounding", "judge_Grounding_explanation",
        "judge_Latency", "judge_final_score",
    ]
    for col in judge_cols:
        df[col] = ""
        df[col] = df[col].astype(object)

    for i, row in df.iterrows():
        print(f"[{i + 1}/{len(df)}] id={row['id']}")
        if i > 0:
            time.sleep(4)  # free-tier quota: 15 requests/minute
        result = judge(document, row["question"], row["generated_answer"])

        ratings = {}
        for crit, key in [("Fluency", "fluency"), ("Grammar", "grammar"), ("Tone", "tone"),
                           ("Length", "length"), ("Grounding", "grounding")]:
            cv = getattr(result, key)
            df.at[i, f"judge_{crit}"] = cv.verdict
            df.at[i, f"judge_{crit}_explanation"] = cv.explanation
            ratings[crit] = cv.verdict

        ratings["Latency"] = latency_rating(row["latency_ms"])
        df.at[i, "judge_Latency"] = ratings["Latency"]
        df.at[i, "judge_final_score"] = compute_final_score(ratings)

    return df


if __name__ == "__main__":
    if "--sanity" in sys.argv:
        sanity_check()
    else:
        df = full_run()
        df.to_excel(OUTPUT_PATH, index=False)
        print(f"\nDone. Judge verdicts written for {len(df)} rows to {OUTPUT_PATH}")
