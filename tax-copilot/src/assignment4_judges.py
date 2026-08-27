"""מטלה 4, Task 5: שלושה שופטי Sonnet + מדד קוד אחד.

task-success (fallback לשורות פתוחות שקוד לא יכול לבדוק), faithfulness (מול כל
פלטי ה-tools מה-trace, לא רק צ'אנקי אחזור כמו judges.judge_faithfulness של מטלה 3),
ו-trajectory-sanity (דיבאג בלבד -- לעולם לא בטבלת הניקוד הרשמית, המטלה אוסרת
במפורש מדד path-level: "there is no 'did it call the right tools in the right
order' metric, and there must not be").

refusal_correctness הוא קוד בלבד, בדיוק לפי הוראת המטלה בסעיף 5.2 -- לא judge.

דפוס זהה ל-judges.py של מטלה 3 (CriterionVerdict: explanation לפני verdict),
מועבר ל-Claude Sonnet.
"""

import os
import sys
import time
from typing import Literal

import truststore
from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

from model_providers import call_judge_structured

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
load_dotenv()
truststore.inject_into_ssl()  # אותו עוקף SSL-inspection עצמי כמו agent_team.py

JUDGE_MODEL = "claude-sonnet-5"
Verdict = Literal["good", "ok", "bad"]


class CriterionVerdict(BaseModel):
    explanation: str
    verdict: Verdict


_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


_JSON_TAIL = """
החזר אך ורק JSON תקני, ללא code fences וללא טקסט נוסף:
{"explanation": "נימוק קצר בעברית", "verdict": "good|ok|bad"}"""


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
    # נצפה בפועל: הפרומפט מבקש "אך ורק JSON", אבל לפעמים המודל עדיין פותח בפרוזה
    # (במיוחד כשה-user content ארוך, כמו tool_outputs גדולים) לפני שמגיע ל-JSON.
    # לחלץ את התחום החיצוני {...} במקום לוותר על כל התשובה.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def _claude_judge_call(model: str, system_prompt: str, user_content: str, response_model: type,
                        *, max_attempts: int = 4):
    """כמו llm.call_structured של מטלה 3: לנסות שוב על JSON פגום/עטוף-פרוזה **וגם**
    על שגיאות רשת/עומס חולפות (529 Overloaded, DNS hiccup וכו') -- לפני הגרסה
    הקודמת קריאת ה-API עצמה הייתה מחוץ ל-try/except, כך ש-ConnectError הפיל את
    כל ריצת Task 5 במקום להירשם כניסיון-חוזר יחיד."""
    last_error = None
    for attempt in range(max_attempts):
        try:
            # thinking="disabled": claude-sonnet-5 defaults to extended thinking, which
            # (discovered live) can consume the ENTIRE max_tokens budget on ThinkingBlock
            # alone, leaving zero tokens for the actual JSON -- stop_reason="max_tokens",
            # content=[ThinkingBlock] only, raw text = "". Not needed anyway: the rubric
            # already asks for explanation-before-verdict inside the visible JSON.
            response = _get_client().messages.create(
                model=model, max_tokens=512, system=system_prompt + _JSON_TAIL,
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


def _judge(model: str, system_prompt: str, user_content: str) -> CriterionVerdict:
    """model_providers.call_judge_structured מנתב claude-*/gemini-* -- ברירת המחדל בכל
    קריאה למטה היא JUDGE_MODEL (claude-sonnet-5, הקנוני של המטלה); model הוא אופציה
    לבקרת עלות (src/model_providers.py), לא תחליף שקט."""
    return call_judge_structured(model, system_prompt + _JSON_TAIL, user_content, CriterionVerdict,
                                  claude_call=_claude_judge_call)


TASK_SUCCESS_PROMPT = """אתה שופט הצלחת-משימה (task success) עבור agent מיסוי.
מקבל שאלה, success_criteria שנכתב מראש לפני ההרצה, ותשובת ה-agent. השאלה היחידה:
האם התשובה מקיימת את ה-success_criteria?
good = מקיימת במלואה. ok = מקיימת בכיוון הנכון אך חסרה פרט מהותי/לא מדויקת.
bad = לא מקיימת, או סותרת את הנדרש."""


def judge_task_success(question: str, success_criteria: str, answer: str, *, model: str = JUDGE_MODEL) -> CriterionVerdict:
    """Fallback בלבד -- ראשית מנסים בדיקת-קוד ישירה מול success_criteria
    (ראו assignment4_eval_runner.score_task_success); זה נקרא רק כשהפרדיקט פתוח מהותית."""
    return _judge(model, TASK_SUCCESS_PROMPT,
                  f"שאלה: {question}\n\nsuccess_criteria: {success_criteria}\n\nתשובת ה-agent: {answer}")


FAITHFULNESS_PROMPT = """אתה שופט ביסוס (faithfulness) של תשובת agent בפלטי ה-tools שהוא קרא בפועל.
מקבל שאלה, את כל פלטי ה-tools מה-trace (יכולים לכלול גם תוצאות retrieval וגם תוצאות חישוב),
ואת התשובה. את/ה לא רואה תשובת ייחוס ואינך שופט/ת נכונות עולמית -- רק ביסוס בפלטים שסופקו.
good = כל טענה עובדתית/מספרית בתשובה נתמכת ישירות באחד מפלטי ה-tools. סירוב הוא good
       כשפלטי ה-tools אינם מספקים מענה לשאלה הספציפית שנשאלה.
ok = טענה אחת מנוסחת בקירוב ביחס לפלטים, בלי המצאה ובלי סתירה.
bad = טענה שאינה נתמכת בשום פלט tool, סתירה לפלט tool, או סירוב למרות שהפלטים כן מספקים תשובה."""


def judge_faithfulness(question: str, tool_outputs: str, answer: str, *, model: str = JUDGE_MODEL) -> CriterionVerdict:
    return _judge(model, FAITHFULNESS_PROMPT,
                  f"שאלה: {question}\n\nפלטי tools:\n{tool_outputs or '(לא נקראו tools)'}\n\nתשובה: {answer}")


TRAJECTORY_SANITY_PROMPT = """אתה שופט "שפיות מסלול" (trajectory sanity) של הרצת agent -- דיבאג בלבד,
לעולם לא ניקוד רשמי. מקבל את רצף הצעדים (מחשבה/tool/קלט/פלט) של הרצה אחת.
מטרתך היחידה: לזהות thrash, לולאות, או קריאות tool שלא תרמו כלום -- לא לבדוק אם "הסדר נכון",
כי אין סדר נכון יחיד ו-agent שפתר משימה בפחות צעדים מהצפוי הוא הצלחה, לא בעיה.
good = מסלול הגיוני, בלי חזרות מיותרות. ok = יש קצת עודף (למשל קריאה כפולה לאותו query) שלא הרסני.
bad = לולאה ברורה, thrash, או קריאות tool חוזרות-ונשנות שלא קידמו את התשובה."""


def judge_trajectory_sanity(steps_text: str, *, model: str = JUDGE_MODEL) -> CriterionVerdict:
    return _judge(model, TRAJECTORY_SANITY_PROMPT, f"רצף הצעדים:\n{steps_text}")


def refusal_correctness(answerable: bool, terminal_state: str) -> str:
    """קוד בלבד -- שני כיווני כשל נספרים בנפרד (Task 5.2)."""
    answered = terminal_state == "answered"
    if not answerable:
        return "correct_refusal" if not answered else "false_answer"
    return "correct_answer" if answered else "false_refusal"


VERDICT_SCORE = {"good": 1.0, "ok": 0.5, "bad": 0.0}
