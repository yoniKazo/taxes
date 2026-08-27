"""מטלה 4, Task 3.1: הלולאה בכתיבת יד (~20 שורות) -- להבין מה LangGraph עושה
מתחתיו לפני שסומכים עליו. רץ על משימת multi-hop אחת, מדפיס כל הודעה,
ונשמר כמות שהוא -- לא ייגע בו שוב אחרי היום שנכתב.
"""

import os
import sys

import truststore
from anthropic import Anthropic
from dotenv import load_dotenv

from tools import calculate_tax_refund, calculator, search_tax_corpus

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
load_dotenv()
truststore.inject_into_ssl()  # אותו עוקף SSL-inspection עצמי כמו agent_team.py

MODEL = "claude-haiku-4-5"
MAX_STEPS = 10
SYSTEM = ("אתה יועץ מס ישראלי. ענה אך ורק מתוך מה שה-tools מחזירים. "
          "אם tool נכשל פעמיים, עצור ואמור שאינך יכול להשלים את המשימה. "
          "אל תקרא ל-tool כשהתשובה כבר ידועה לך. סרב בבירור כשאין לך תשובה.")

TOOLS = {t.name: t for t in [search_tax_corpus, calculator, calculate_tax_refund]}
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _anthropic_schema(tool) -> dict:
    schema = tool.args_schema.model_json_schema()
    return {"name": tool.name, "description": tool.description,
            "input_schema": {"type": "object", "properties": schema["properties"],
                              "required": schema.get("required", [])}}


ANTHROPIC_TOOLS = [_anthropic_schema(t) for t in TOOLS.values()]


def run(task: str) -> str:
    messages = [{"role": "user", "content": task}]
    for step in range(MAX_STEPS):
        resp = client.messages.create(model=MODEL, max_tokens=1024, system=SYSTEM,
                                       tools=ANTHROPIC_TOOLS, messages=messages)
        print(f"\n--- צעד {step} (stop_reason={resp.stop_reason}) ---")
        for block in resp.content:
            print(block)
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text")
        messages.append({"role": "assistant", "content": resp.content})
        results = [
            {"type": "tool_result", "tool_use_id": b.id, "content": TOOLS[b.name].invoke(b.input)}
            for b in resp.content if b.type == "tool_use"
        ]
        messages.append({"role": "user", "content": results})
    return "לא הושלם תוך המספר המרבי של צעדים."


if __name__ == "__main__":
    # mh6 מ-assignment4/data/tasks.csv -- multi-hop אמיתי: retrieval (שיעורי עצמאי) +
    # calculator + calculate_tax_refund (שכיר), שלושת ה-tools יחד.
    task = ("לשכיר עם משכורת 20,000 ₪ לחודש (גבר, ללא נקודות זיכוי נוספות) ולעצמאי עם אותה הכנסה חודשית "
            "— למי דמי הביטוח הלאומי ומס הבריאות גבוהים יותר בחודש, ובכמה?")
    print(f"### משימה: {task}")
    answer = run(task)
    print("\n=== תשובה סופית ===")
    print(answer)
