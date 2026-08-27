"""מטלה 4, Task 3.2: ה-agent המלא ב-LangGraph. אותם שלושה tools כמו raw_loop.py,
system prompt עם כללי העצירה, שלוש רשתות ביטחון (Task 3.3), ו-tracing מלא ל-JSONL
(Task 3.4). break_tool מממש את Task 3.5 (שבירת tool בכוונה למשימות tool_fails).
"""

import os
import sys
import time

import truststore
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, ToolMessage


def _extract_text(content: str | list) -> str:
    """content.msg יכול להיות str (Claude) או list של content blocks (Gemini הילידי) --
    מחלץ את הטקסט מכל צורה."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent

from agent_tracing import JsonlTracer, REFUSAL_MARKER, RunSummary, SafetyNets, StepRecord
from model_providers import build_chat_model
from tools import calculate_tax_refund, calculator, search_tax_corpus

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
load_dotenv()
truststore.inject_into_ssl()  # אותו עוקף SSL-inspection עצמי כמו agent_team.py/raw_loop.py

MODEL = "claude-haiku-4-5"

SYSTEM_PROMPT = f"""אתה יועץ מס ישראלי שמשתמש בכלים כדי לענות בדיוק, לא לנחש.

כללים מחייבים:
1. ענה אך ורק מתוך מה שה-tools החזירו בפועל -- אל תשתמש בידע חיצוני לעובדות מספריות/שיעורי מס.
2. אם tool נכשל (מחזיר "ERROR: ...") פעמיים ברצף, עצור מיד ואמור בדיוק את המשפט: "{REFUSAL_MARKER}"
3. אל תקרא לאותו tool שוב על אותה שאלה בדיוק אם התשובה כבר ידועה לך מתוצאה קודמת באותה שיחה.
4. אם התשובה אינה נמצאת בשום tool זמין (לא בקורפוס ולא ניתנת לחישוב), החזר בדיוק את המשפט: \
"{REFUSAL_MARKER}" -- בלי לנחש ובלי חיפוש ממושך.
"""

DEFAULT_TOOLS = [search_tax_corpus, calculator, calculate_tax_refund]


def broken_tools(broken_name: str) -> list:
    """Task 3.5: tool אחד מוחלף בגרסה ששוברת את עצמה בכוונה, לבדיקת tool_fails."""

    def _broken(**_kwargs) -> str:
        return "ERROR: השירות אינו זמין כרגע. tool זה אינו פעיל -- אל תנסה שוב יותר מפעם אחת."

    out = []
    for t in DEFAULT_TOOLS:
        if t.name == broken_name:
            out.append(StructuredTool.from_function(
                func=_broken, name=t.name, description=t.description, args_schema=t.args_schema,
            ))
        else:
            out.append(t)
    return out


def run_agent_task(
    task: str,
    *,
    task_id: str = "adhoc",
    run: int = 1,
    tools: list | None = None,
    nets: SafetyNets | None = None,
    tracer: JsonlTracer | None = None,
    feedback: str | None = None,
    system_prompt: str | None = None,
    model: str = MODEL,
) -> RunSummary:
    """מריץ משימה אחת מקצה לקצה. תמיד מחזיר RunSummary -- חריגת רשת ביטחון או
    שגיאה הן outcome מתועד (terminal_state), לעולם לא חריגה שמקפיצה למעלה.

    feedback: הסבר judge מסבב evaluator-optimizer קודם (Task 4) -- מצורף למשימה
    כבקשת תיקון, בלי לשנות את ה-system prompt או להתחיל שיחה חדשה מאפס."""
    tools = tools if tools is not None else DEFAULT_TOOLS
    nets = nets or SafetyNets()
    task_text = task if not feedback else (
        f"{task}\n\n(תיקון מבוקש: השופט מצא בעיות בתשובה הקודמת -- {feedback}. "
        "תקן את התשובה בהתאם, תוך שימוש חוזר בתוצאות ה-tools אם עדיין רלוונטיות.)"
    )

    # build_chat_model dispatches claude-*/gemini-* to the right LangChain chat class --
    # ראו src/model_providers.py. max_retries על Claude: 529 "Overloaded" חולף לא אמור
    # להפיל ריצה שלמה ולהירשם כ-terminal_state="error".
    llm_model = build_chat_model(model)
    graph = create_react_agent(llm_model, tools, prompt=system_prompt or SYSTEM_PROMPT)

    start = time.perf_counter()
    step = 0
    total_in = total_out = 0
    tool_calls = 0
    tools_used: list[str] = []
    terminal_state = "error"
    answer = ""
    breach_reason: str | None = None
    seen = 0
    pending: dict[str, tuple[StepRecord, float]] = {}
    tool_outputs: list[str] = []

    try:
        for state in graph.stream(
            {"messages": [("user", task_text)]},
            config={"recursion_limit": nets.max_iterations * 2 + 4},
            stream_mode="values",
        ):
            messages = state["messages"]
            new_messages = messages[seen:]
            seen = len(messages)

            for msg in new_messages:
                if isinstance(msg, AIMessage):
                    step += 1
                    usage = msg.usage_metadata or {}
                    total_in += usage.get("input_tokens", 0)
                    total_out += usage.get("output_tokens", 0)
                    thought = _extract_text(msg.content)
                    calls = msg.tool_calls or []
                    if calls:
                        for call in calls:
                            tool_calls += 1
                            tools_used.append(call["name"])
                            rec = StepRecord(
                                task_id, run, step, thought, call["name"], call["args"], None, 0.0,
                                usage.get("input_tokens", 0), usage.get("output_tokens", 0),
                            )
                            pending[call["id"]] = (rec, time.perf_counter())
                    else:
                        answer = thought
                        terminal_state = "refused" if REFUSAL_MARKER in thought else "answered"
                        if tracer:
                            tracer.write_step(StepRecord(
                                task_id, run, step, thought, None, None, None, 0.0,
                                usage.get("input_tokens", 0), usage.get("output_tokens", 0),
                            ))
                elif isinstance(msg, ToolMessage):
                    entry = pending.pop(msg.tool_call_id, None)
                    if entry:
                        rec, t0 = entry
                        rec.output = msg.content if isinstance(msg.content, str) else str(msg.content)
                        rec.duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                        tool_outputs.append(f"[{rec.tool}] קלט: {rec.input} -> {rec.output}")
                        if tracer:
                            tracer.write_step(rec)

            elapsed_s = time.perf_counter() - start
            breach_reason = nets.breach(step, total_in + total_out, elapsed_s)
            if breach_reason:
                break
    except Exception as e:  # noqa: BLE001 -- כל כשל הופך ל-terminal_state="error", לא קורס
        terminal_state = "error"
        answer = f"שגיאה: {e}"

    if breach_reason:
        terminal_state = "cap_breached"
        answer = answer or f"לא הושלם תוך המגבלות: חריגת רשת ביטחון ({breach_reason})."

    total_wall_ms = round((time.perf_counter() - start) * 1000, 1)
    summary = RunSummary(
        task_id=task_id, run=run, steps=step, total_input_tokens=total_in,
        total_output_tokens=total_out, total_wall_ms=total_wall_ms, terminal_state=terminal_state,
        tool_calls=tool_calls, tools_used=tools_used, answer=answer, breach=breach_reason,
        tool_outputs="\n".join(tool_outputs),
    )
    if tracer:
        tracer.write_summary(summary)
    return summary


if __name__ == "__main__":
    # Task 3: dry run -- 3 משימות, הרצה אחת, לבדוק trace + ספירת טוקנים לפני הרצה גדולה יותר.
    _TRACE_PATH = os.path.join(os.path.dirname(__file__), "..", "assignment4", "data", "traces", "agent_dryrun.jsonl")
    tracer = JsonlTracer(_TRACE_PATH)
    dry_run_tasks = [
        ("s2", "מהי תקרת הפטור ממס שבח לדירת מגורים יחידה?"),
        ("mh1", "כמה מס רכישה אשלם על דירה שנייה (לא דירה יחידה) בשווי 4,000,000 ₪?"),
        ("nt1", "מה אתה יכול לעזור לי איתו?"),
    ]
    for task_id, task in dry_run_tasks:
        print(f"\n### dry-run {task_id}: {task}")
        result = run_agent_task(task, task_id=task_id, run=1, tracer=tracer)
        print(result)
