"""מטלה 4, Task 4: Evaluator-Optimizer.

"ה-rubric הישן שלך" שהמטלה מדברת עליו הוא הרוברייק **האמיתית** של מטלה 2
(assignment2/assignment2_rubric.md) -- לא rubric חדש שהומצא לצורך המטלה הזו.
RUBRIC_TEXT / JudgeOutput / compute_final_score מיובאים כמות שהם מ-assignment2_judge.py
(cumulative pass bar 4/6 good + 0 bad; go/no-go: grounding לא-good או length=bad -> fail
אוטומטי). ה-judge עובר מ-Gemini ל-Claude Sonnet, וה-`document` היחיד שה-QA judge ציפה
לו מוחלף כאן בהקשר תוצאות ה-tools מה-trace (RunSummary.tool_outputs) -- זה מה ש-
"grounding" נבדק מולו עבור agent, לא מסמך יחיד.

Latency נשאר כמו במקור: נגזר בקוד (agent_tracing), לעולם לא נשלח לשופט.
"""

import os
import sys
import time

import truststore
from anthropic import Anthropic
from dotenv import load_dotenv

from agent import run_agent_task
from agent_tracing import JsonlTracer, SafetyNets
from assignment2_judge import JudgeOutput, RUBRIC_TEXT, compute_final_score
from model_providers import call_judge_structured

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
load_dotenv()
truststore.inject_into_ssl()  # אותו עוקף SSL-inspection עצמי כמו agent_team.py

JUDGE_MODEL = "claude-sonnet-5"
MAX_REVISION_ROUNDS = 2

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


JUDGE_SYSTEM_PROMPT = f"""אתה שופט איכות (LLM judge) שמעריך תשובות של agent מיסוי שמשתמש בכלים (tools).
החל את הרוברייק הבאה *במדויק* כפי שהיא מנוסחת -- אל תשתמש בסטנדרטים משלך:
{RUBRIC_TEXT}

הבדל מהמקור: לצורך "grounding" כאן, המקור היחיד המותר הוא **פלטי ה-tools שסופקו לך**
(לא מסמך יחיד, ולא ידע עולם) -- ה-agent עשוי לשלב תוצאות retrieval וגם תוצאות חישוב.

לכל אחד מ-5 הקריטריונים (fluency, grammar, tone, length, grounding) החזר `explanation` \
(הסבר קצר בעברית) ולפני זה נמק במדויק לפי הרוברייק, ואז `verdict` (good/ok/bad).
החזר אך ורק JSON תקני, ללא טקסט נוסף, ללא code fences:
{{"fluency": {{"explanation": "...", "verdict": "good|ok|bad"}}, "grammar": {{...}}, \
"tone": {{...}}, "length": {{...}}, "grounding": {{...}}}}"""


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```", 2)
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    # ראו assignment4_judges._strip_fence -- אותה תופעה (פרוזה לפני ה-JSON), אותו תיקון.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def _claude_judge_call(model: str, system_prompt: str, user_content: str, response_model: type,
                        *, max_attempts: int = 4):
    """הנתיב הקיים מול Anthropic SDK ישיר -- retry על רשת/JSON, thinking disabled
    (claude-sonnet-5 מפעיל extended thinking כברירת מחדל, שיכול לצרוך את כל תקציב
    ה-max_tokens על בלוק החשיבה בלבד; הרוברייק כבר מבקשת explanation-לפני-verdict
    בתוך ה-JSON הגלוי, אז אין צורך בבלוק חשיבה נפרד)."""
    last_error = None
    for attempt in range(max_attempts):
        try:
            response = _get_client().messages.create(
                model=model, max_tokens=1024, system=system_prompt,
                thinking={"type": "disabled"}, messages=[{"role": "user", "content": user_content}],
            )
            raw = "".join(b.text for b in response.content if b.type == "text")
            return response_model.model_validate_json(_strip_fence(raw))
        except Exception as e:  # noqa: BLE001 -- כל כשל (רשת/JSON) מנסה שוב, לא קורס מיד
            last_error = e
            wait = min(2 ** attempt, 15)
            print(f"  (retry {attempt + 1}/{max_attempts} בעוד {wait}s: {type(e).__name__}: {str(e)[:150]!r})")
            if attempt < max_attempts - 1:
                time.sleep(wait)
    raise last_error


def judge_agent_answer(tool_outputs: str, question: str, answer: str, *, judge_model: str = JUDGE_MODEL) -> JudgeOutput:
    """model_providers.call_judge_structured מנתב claude-*/gemini-* -- ל-Claude מפעיל
    את _claude_judge_call (retry + thinking-disabled + חילוץ JSON), ל-Gemini את
    llm.call_structured הקיים (שכבר מטפל בקילוף fence/גרשיים)."""
    user_content = f"פלטי הכלים (tools) שהיו זמינים ל-agent:\n{tool_outputs or '(לא נקראו tools)'}\n\n" \
                   f"שאלה: {question}\n\nתשובת ה-agent להערכה: {answer}"
    return call_judge_structured(judge_model, JUDGE_SYSTEM_PROMPT, user_content, JudgeOutput,
                                  claude_call=_claude_judge_call)


def _ratings_dict(output: JudgeOutput) -> dict:
    return {
        "Fluency": output.fluency.verdict,
        "Grammar": output.grammar.verdict,
        "Tone": output.tone.verdict,
        "Length": output.length.verdict,
        "Grounding": output.grounding.verdict,
    }


def _explanation_summary(output: JudgeOutput) -> str:
    dumped = output.model_dump()
    problems = [f"{name} ({cv['verdict']}): {cv['explanation']}"
                for name, cv in dumped.items() if cv["verdict"] != "good"]
    return " | ".join(problems) if problems else "אין בעיות ספציפיות שדווחו."


def run_with_evaluator_optimizer(
    task: str, *, task_id: str = "adhoc", run: int = 1,
    tools=None, nets: SafetyNets | None = None, tracer: JsonlTracer | None = None,
    max_rounds: int = MAX_REVISION_ROUNDS,
    model: str = "claude-haiku-4-5", judge_model: str = JUDGE_MODEL,
    system_prompt: str | None = None,
) -> dict:
    """מריץ agent, שופט מול הרוברייק, ומתקן עד max_rounds פעמים בדחייה.
    model/judge_model: ברירת המחדל היא הקונפיגורציה הקנונית של המטלה -- Gemini הוא
    אופציה לבקרת עלות (src/model_providers.py), לא תחליף שקט להשוואה הרשמית.
    מחזיר dict עם ה-RunSummary הסופי + פרטי השיפוט (verdict/ratings/rounds)."""
    feedback = None
    summary = None
    verdict = "fail"
    ratings: dict = {}
    rounds_used = 0

    for round_num in range(max_rounds + 1):
        summary = run_agent_task(task, task_id=task_id, run=run, tools=tools, nets=nets,
                                  tracer=tracer, feedback=feedback, model=model, system_prompt=system_prompt)
        if summary.terminal_state in ("cap_breached", "error"):
            # אין מה לשפוט תשובה שלא הופקה -- outcome מתועד כמו שהוא.
            verdict = "fail"
            ratings = {}
            break

        judged = judge_agent_answer(summary.tool_outputs, task, summary.answer, judge_model=judge_model)
        ratings = _ratings_dict(judged)
        verdict = compute_final_score(ratings)
        rounds_used = round_num
        if verdict == "pass" or round_num == max_rounds:
            break
        feedback = _explanation_summary(judged)

    return {
        "summary": summary,
        "verdict": verdict,
        "ratings": ratings,
        "rounds_used": rounds_used,
    }


if __name__ == "__main__":
    result = run_with_evaluator_optimizer(
        "כמה מס רכישה אשלם על דירה שנייה (לא דירה יחידה) בשווי 4,000,000 ₪?", task_id="mh1", run=1,
    )
    print(result["summary"])
    print("verdict:", result["verdict"], "| ratings:", result["ratings"], "| rounds:", result["rounds_used"])
