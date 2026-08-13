"""Exercise 1c: grounded Q&A over a single document."""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)

MODEL = "gemini-flash-lite-latest"

SYSTEM_PROMPT = """ענה אך ורק לפי המסמך המצורף. אל תשתמש בידע חיצוני ואל תנחש.
כאשר אתה עונה, צטט את הקטע המדויק מהמסמך שתומך בתשובה.
אם התשובה אינה מופיעה במסמך, השב אך ורק במשפט: "לא מצאתי את זה במסמך."""


def answer_question(document: str, question: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"מסמך:\n{document}\n\nשאלה: {question}",
            },
        ],
    )
    return response.choices[0].message.content


def main() -> None:
    file_path = sys.argv[1] if len(sys.argv) > 1 else input("נתיב הקובץ: ")
    question = sys.argv[2] if len(sys.argv) > 2 else input("שאלה: ")

    with open(file_path, "r", encoding="utf-8") as f:
        document = f.read()

    print(answer_question(document, question))


if __name__ == "__main__":
    main()
