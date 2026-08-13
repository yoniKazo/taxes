"""Systematic grounded-QA experiment over data/tax_notes.md.

Main matrix: 3 questions x 3 system-prompt variants x 3 temperatures, on Gemini (27 runs).
The local model (bloomz-560m) is run only ONCE, as a single reference data point —
each local CPU call with a ~1,400-token context takes on the order of minutes, so
running the full 27-combination matrix locally too was impractical; see the note
written into experiment_results.md.
Writes the full result table to experiment_results.md.
"""

import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

import local_llm

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEMINI_MODEL = "gemini-flash-lite-latest"
LOCAL_MODEL = local_llm.MODEL
TEMPERATURES = [0, 0.5, 1]
DOC_PATH = os.path.join(SCRIPT_DIR, "..", "data", "tax_notes.md")
RESULTS_PATH = os.path.join(SCRIPT_DIR, "experiment_results.md")
LOCAL_CONTEXT_BUDGET = local_llm.CONTEXT_TOKEN_BUDGET

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)

QUESTIONS = [
    {
        "label": "יש-במסמך",
        "text": "מהו שיעור המס במדרגה השנייה, ובאיזה טווח הכנסה חודשי הוא חל?",
    },
    {
        "label": "לא-קיים-כלל",
        "text": "מהו שיעור מס הרכישה על דירה שנייה בישראל?",
    },
    {
        "label": "מתחכמת",
        "text": "כמה נקודות זיכוי מקבל עצמאי, ומהו שיעור המקדמות שהוא משלם?",
    },
]

PROMPT_VARIANTS = [
    {
        "label": "V1-קפדני-מפורט",
        "text": (
            "ענה אך ורק לפי המסמך המצורף. אל תשתמש בידע חיצוני ואל תנחש.\n"
            "כאשר אתה עונה, צטט את הקטע המדויק מהמסמך שתומך בתשובה.\n"
            'אם התשובה אינה מופיעה במסמך, השב אך ורק במשפט: "לא מצאתי את זה במסמך."'
        ),
    },
    {
        "label": "V2-תמציתי",
        "text": (
            "ענה רק לפי המסמך שסופק. צטט מקור. "
            'אם אין תשובה במסמך — כתוב: "לא מצאתי את זה במסמך."'
        ),
    },
    {
        "label": "V3-פורמלי-פורמט-קבוע",
        "text": (
            "אתה עוזר קפדני. תשובתך חייבת להתבסס אך ורק על הטקסט הבא ואסור להשתמש בידע חיצוני בשום אופן.\n"
            "השב בפורמט הבא בדיוק:\n"
            'תשובה: <התשובה, או "לא מצאתי את זה במסמך.">\n'
            'מקור: <ציטוט מדויק מהמסמך, או "-">'
        ),
    },
]


def ask_gemini(document: str, question: str, system_prompt: str, temperature: float) -> str:
    for attempt in range(5):
        try:
            response = client.chat.completions.create(
                model=GEMINI_MODEL,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"מסמך:\n{document}\n\nשאלה: {question}"},
                ],
            )
            return response.choices[0].message.content.strip()
        except RateLimitError:
            if attempt == 4:
                raise
            time.sleep(15)


def run_experiment() -> list[dict]:
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        document = f.read()

    rows = []
    # Main matrix: Gemini only (fast hosted calls).
    total = len(QUESTIONS) * len(PROMPT_VARIANTS) * len(TEMPERATURES) + 1
    done = 0

    for question in QUESTIONS:
        for variant in PROMPT_VARIANTS:
            for temperature in TEMPERATURES:
                done += 1
                print(f"[{done}/{total}] Gemini | {question['label']} | {variant['label']} | temp={temperature}")
                if done > 1:
                    time.sleep(4)  # free-tier quota is 15 requests/minute
                try:
                    answer = ask_gemini(document, question["text"], variant["text"], temperature)
                except Exception as e:
                    answer = f"[שגיאה: {e}]"
                rows.append({
                    "model": "Gemini",
                    "question_label": question["label"],
                    "question_text": question["text"],
                    "variant_label": variant["label"],
                    "temperature": temperature,
                    "answer": answer,
                })

    # Single reference data point for the local model — see the slowness note in write_results().
    done += 1
    ref_question, ref_variant, ref_temperature = QUESTIONS[0], PROMPT_VARIANTS[0], TEMPERATURES[0]
    print(f"[{done}/{total}] Local (bloomz-560m) | {ref_question['label']} | {ref_variant['label']} | temp={ref_temperature}")
    try:
        local_answer = local_llm.answer_question(
            document, ref_question["text"], ref_temperature, ref_variant["text"]
        )
    except Exception as e:
        local_answer = f"[שגיאה: {e}]"
    rows.append({
        "model": "Local (bloomz-560m)",
        "question_label": ref_question["label"],
        "question_text": ref_question["text"],
        "variant_label": ref_variant["label"],
        "temperature": ref_temperature,
        "answer": local_answer,
    })

    return rows


def write_results(rows: list[dict]) -> None:
    lines = []
    lines.append("# תוצאות ניסוי Q&A ממוסמך — data/tax_notes.md\n")
    lines.append(
        "**המחקר המרכזי — Gemini בלבד:** 3 שאלות × 3 נוסחי system prompt × 3 טמפרטורות (0 / 0.5 / 1) = 27 הרצות.\n"
        "**המודל המקומי (`bloomz-560m`):** הרצה אחת בלבד לצורך רפרנס/השוואה — ראו הסבר למטה.\n"
    )
    lines.append(
        "### למה המודל המקומי הורץ פעם אחת בלבד\n"
        "בסבב ראשון ניסינו להריץ את כל 54 השילובים (27 מול Gemini + 27 מול המודל המקומי). "
        "כל קריאה מקומית עם הקשר של כ-1,400 טוקנים לקחה על סדר גודל של דקות על CPU — "
        "27 קריאות כאלה היו מאריכות את הניסוי לעשרות דקות ללא תועלת מחקרית מספקת "
        "(האיכות כבר נראתה חלשה/חוזרת-על-עצמה בבדיקת התקינות הראשונית). לכן הוחלט להתמקד "
        "ב-27 ההרצות מול Gemini, ולהשאיר הרצה מקומית אחת כנקודת רפרנס להשוואת איכות.\n"
    )

    lines.append("## מתודולוגיה\n")
    lines.append("### שאלות\n")
    for q in QUESTIONS:
        lines.append(f"- **{q['label']}:** {q['text']}")
    lines.append("")

    lines.append("### נוסחי system prompt\n")
    for v in PROMPT_VARIANTS:
        lines.append(f"**{v['label']}:**")
        lines.append(f"> {v['text'].replace(chr(10), chr(10) + '> ')}")
        lines.append("")

    lines.append(
        f"### הערת מגבלת הקשר למודל המקומי\n"
        f"`data/tax_notes.md` המלא מתורגם לכ-7,734 טוקנים לפי הטוקנייזר של `bloomz-560m`, "
        f"בעוד חלון ההקשר של המודל הוא 2,048 טוקנים בלבד. לכן, עבור המודל המקומי, המסמך "
        f"נחתך ל-{LOCAL_CONTEXT_BUDGET} הטוקנים הראשונים (לפי הטוקנייזר עצמו) לפני הבנייה של הפרומפט. "
        f"מול Gemini מוזן המסמך המלא ללא חיתוך.\n"
    )

    lines.append("## תוצאות\n")
    lines.append("| # | מודל | סוג שאלה | וריאנט פרומפט | טמפ׳ | תשובה |")
    lines.append("|---|---|---|---|---|---|")
    for i, row in enumerate(rows, start=1):
        answer_escaped = row["answer"].replace("\n", " ").replace("|", "\\|")
        lines.append(
            f"| {i} | {row['model']} | {row['question_label']} | {row['variant_label']} "
            f"| {row['temperature']} | {answer_escaped} |"
        )

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    results = run_experiment()
    write_results(results)
    print(f"\nDone. {len(results)} rows written to {RESULTS_PATH}")
