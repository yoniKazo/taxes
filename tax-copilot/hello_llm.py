"""Exercise 1 + 1b: call Claude via the OpenAI-compatible client, then engineer the call."""

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)

MODEL = "gemini-flash-lite-latest"


def basic_call() -> None:
    print("=== Exercise 1: Hello, LLM ===")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Say hello in one sentence."}],
    )
    print(response.choices[0].message.content)


def system_prompt_call() -> None:
    print("\n=== Exercise 1b.1: system prompt (persona) ===")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "אתה יועץ מס ידידותי אך מדויק. ענה במשפט אחד בעברית.",
            },
            {"role": "user", "content": "האם כדאי לי לפתוח עוסק פטור?"},
        ],
    )
    print(response.choices[0].message.content)


def temperature_call() -> None:
    print("\n=== Exercise 1b.2: temperature 0 vs 1 ===")
    question = "תן טיפ אחד לחיסכון במס."
    for temperature in (0, 0, 1, 1):
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": question}],
            temperature=temperature,
        )
        print(f"[temperature={temperature}] {response.choices[0].message.content}")


class Answer(BaseModel):
    answer: str
    confidence: float


def structured_output_call() -> None:
    print("\n=== Exercise 1b.3: structured JSON output ===")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "ענה אך ורק ב-JSON תקני בפורמט "
                    '{"answer": "...", "confidence": 0.0-1.0}, ללא טקסט נוסף.'
                ),
            },
            {"role": "user", "content": "האם הוצאות נסיעה לעבודה מוכרות למס?"},
        ],
    )
    raw = response.choices[0].message.content
    if raw.startswith("```"):
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    parsed = json.loads(raw)
    print(f"(a) json.loads -> answer={parsed['answer']!r} confidence={parsed['confidence']}")

    validated = Answer.model_validate_json(raw)
    print(f"(b) pydantic   -> answer={validated.answer!r} confidence={validated.confidence}")


if __name__ == "__main__":
    basic_call()
    system_prompt_call()
    temperature_call()
    structured_output_call()
