"""מטלה 4: שכבת dispatch יחידה לבחירת ספק/מודל, לשימוש בכל מקום שמריצים agent או judge --
מגרש המשחקים, מנהל הקונפיגורציות, ה-CLI. ברירת המחדל בכל מקום היא הקונפיגורציה הקנונית
של המטלה (`claude-haiku-4-5` agent, `claude-sonnet-5` judge); Gemini הוא אופציה זמינה
לבקרת עלות, לא תחליף שקט להשוואה הרשמית של Task 5.

**חשוב:** ל-agent (tool-calling רב-תורי) Gemini מחובר דרך `ChatGoogleGenerativeAI` (SDK
ילידי), **לא** דרך `ChatOpenAI`/ה-endpoint התואם-OpenAI. נבדק בפועל: Gemini's newer
"thinking" models (כולל `gemini-flash-lite-latest`) מצרפים `thought_signature` ל-tool
call, וחייבים לקבל אותו בחזרה בתור הבא כדי שהשיחה תמשיך -- אחרת 400
`INVALID_ARGUMENT: Function call is missing a thought_signature`. ה-endpoint התואם-OpenAI
מחזיר tool_calls תקינים בקריאה הראשונה (זה מה שבדיקת ה-smoke הראשונית בדקה), אבל
`ChatOpenAI` של LangChain לא משמר את השדה הזה כשהוא בונה מחדש את ה-tool_call להודעה
הבאה -- כך שכל משימה עם יותר מקריאת-כלי אחת קורסת בתור השני. `ChatGoogleGenerativeAI`
(ה-SDK הילידי) כן משמר את זה נכון (נבדק: round-trip דו-שלבי עם calculator עבד תקין).
ל-judge (single-turn, בלי tool use) הבעיה לא רלוונטית -- `llm.call_structured` (ה-endpoint
התואם-OpenAI הקיים) ממשיך לעבוד כרגיל.
"""

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.rate_limiters import BaseRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

import llm as gemini_llm

CLAUDE_PREFIX = "claude-"
GEMINI_PREFIX = "gemini-"


class _SharedGeminiThrottle(BaseRateLimiter):
    """עוטף את gemini_llm._wait_for_slot() הקיים (`.claude/rules/hosted-llm-quota.md`)
    כך שקריאות ה-agent (דרך ChatGoogleGenerativeAI) חולקות את אותו שעון גלובלי עם קריאות
    ה-judge (דרך llm.call_text) -- שני מנגנוני throttle נפרדים היו יכולים לחפוף ולעבור
    יחד את תקרת 15 req/min גם אם כל אחד בנפרד מכבד אותה."""

    def acquire(self, *, blocking: bool = True) -> bool:
        gemini_llm._wait_for_slot()
        return True

    async def aacquire(self, *, blocking: bool = True) -> bool:
        gemini_llm._wait_for_slot()
        return True


_GEMINI_THROTTLE = _SharedGeminiThrottle()


def build_chat_model(model: str) -> BaseChatModel:
    """ל-agent (LangGraph, tool-calling). claude-* -> ChatAnthropic (כמו היום).
    gemini-* -> ChatGoogleGenerativeAI (SDK ילידי -- לא ChatOpenAI, ראו docstring למעלה
    למה חובה), עם rate_limiter משותף מול llm.py."""
    if model.startswith(CLAUDE_PREFIX):
        return ChatAnthropic(model=model, max_tokens=1024, max_retries=4)
    if model.startswith(GEMINI_PREFIX):
        return ChatGoogleGenerativeAI(
            model=model, google_api_key=os.environ["GEMINI_API_KEY"], rate_limiter=_GEMINI_THROTTLE,
        )
    raise ValueError(f'לא ידוע לאיזה ספק שייך המודל "{model}" (צפוי prefix "{CLAUDE_PREFIX}" או "{GEMINI_PREFIX}")')


def call_judge_structured[T: BaseModel](
    model: str, system_prompt: str, user_content: str, response_model: type[T],
    *, claude_call=None,
) -> T:
    """ל-judges (evaluator-optimizer + Task 5). claude-* -> הנתיב הקיים היום מול Anthropic
    SDK ישיר (מועבר דרך claude_call, כי לכל judge יש retry/thinking-disabled/JSON-extraction
    משלו כבר בנוי -- הפונקציה הזו לא כופה מימוש Claude אחיד, רק מנתבת). gemini-* ->
    llm.call_structured() הקיים, שכבר מטפל בקילוף fence ותיקון גרשיים של Gemini."""
    if model.startswith(CLAUDE_PREFIX):
        if claude_call is None:
            raise ValueError("model הוא Claude אבל לא סופק claude_call -- ראו assignment4_judges._judge")
        return claude_call(model, system_prompt, user_content, response_model)
    if model.startswith(GEMINI_PREFIX):
        parsed, _raw = gemini_llm.call_structured(system_prompt, user_content, response_model, model=model)
        return parsed
    raise ValueError(f'לא ידוע לאיזה ספק שייך המודל "{model}" (צפוי prefix "{CLAUDE_PREFIX}" או "{GEMINI_PREFIX}")')
