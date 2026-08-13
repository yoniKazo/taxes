"""Task 2: generate an answer for every question in data/tax_qa_dataset.md,
grounded in ../data/tax_notes.md, and write assignment_02.xlsx with the
measured fields plus blank rubric columns for Task 3 (human) and Task 6 (judge).
"""

import os
import re
import sys
import time

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_PATH = os.path.join(SCRIPT_DIR, "..", "data", "tax_notes.md")
DATASET_PATH = os.path.join(SCRIPT_DIR, "..", "assignment2", "data", "tax_qa_dataset.md")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "assignment2", "assignment_02.xlsx")

GEMINI_MODEL = "gemini-flash-lite-latest"

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)

# System prompt derived directly from assignment2_rubric.md (Length + Grounding bands).
SYSTEM_PROMPT = """אתה יועץ מס ידידותי ומדויק, שעונה לשכירים בישראל על שאלות לגבי מיסוי, ביטוח לאומי, פנסיה וקרן השתלמות.

כללים מחייבים:
1. ענה אך ורק לפי המסמך המצורף. אל תשתמש בידע חיצוני ואל תמציא מספרים, שיעורים או כללים שאינם במסמך.
2. אם התשובה אינה מופיעה במסמך (למשל שאלות על עצמאים, נדל"ן, מע"מ), השב אך ורק במשפט: "לא מצאתי את זה במסמך."
3. אורך התשובה: 1–3 משפטים ממוקדים. אל תפרט מעבר לכך.
4. ענה בטון חם ומקצועי, לא כהעתקה יבשה של קטע מהמסמך."""


def load_document() -> str:
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        return f.read()


def load_questions() -> list[dict]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    questions = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 3 or not cells[0].isdigit():
            continue
        questions.append({"id": int(cells[0]), "category": cells[1], "question": cells[2]})
    return questions


def ask(document: str, question: str, system_prompt: str = SYSTEM_PROMPT, temperature: float | None = None) -> dict:
    kwargs = {} if temperature is None else {"temperature": temperature}
    for attempt in range(5):
        try:
            start = time.perf_counter()
            response = client.chat.completions.create(
                model=GEMINI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"מסמך:\n{document}\n\nשאלה: {question}"},
                ],
                **kwargs,
            )
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            answer = response.choices[0].message.content.strip()
            answer = re.sub(r"^```(json)?|```$", "", answer).strip()
            return {
                "generated_answer": answer,
                "latency_ms": latency_ms,
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
        except RateLimitError:
            if attempt == 4:
                raise
            time.sleep(15)


def generate() -> pd.DataFrame:
    document = load_document()
    questions = load_questions()

    rows = []
    for i, q in enumerate(questions):
        print(f"[{i + 1}/{len(questions)}] {q['category']} | {q['question'][:50]}")
        if i > 0:
            time.sleep(4)  # free-tier quota: 15 requests/minute
        result = ask(document, q["question"])
        rows.append({**q, **result})

    df = pd.DataFrame(rows)
    for col in ["Fluency", "Grammar", "Tone", "Length", "Grounding", "Latency", "final_score"]:
        df[col] = ""
    return df


if __name__ == "__main__":
    df = generate()
    df.to_excel(OUTPUT_PATH, index=False)
    print(f"\nDone. {len(df)} rows written to {OUTPUT_PATH}")
