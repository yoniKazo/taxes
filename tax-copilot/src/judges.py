"""Task 5: the four LLM judges, plus the code-only refusal check.

Each judge is a separate function with its own narrow prompt, so "faithfulness
never sees the reference answer" and "context relevance never sees the generated
answer" are structural facts rather than discipline you have to remember. A
single judge_everything() would silently leak all four contexts into each other.

Same pattern as assignment2_judge.py: rubric verbatim in the prompt, Pydantic
schema, and `explanation` BEFORE `verdict` so the model reasons before ruling
instead of rationalising a verdict it already emitted.
"""

import hashlib
import sys
from typing import Literal

from pydantic import BaseModel

from llm import JUDGE_MODEL, call_structured

sys.stdout.reconfigure(encoding="utf-8")

Verdict = Literal["good", "ok", "bad"]


class CriterionVerdict(BaseModel):
    explanation: str
    verdict: Verdict


_JSON_TAIL = """
החזר אך ורק JSON תקני, ללא code fences וללא טקסט נוסף:
{"explanation": "נימוק קצר בעברית", "verdict": "good|ok|bad"}"""


def _judge(system_prompt: str, user_content: str) -> CriterionVerdict:
    parsed, _ = call_structured(system_prompt + _JSON_TAIL, user_content,
                                CriterionVerdict, model=JUDGE_MODEL)
    return parsed


CONTEXT_RELEVANCE_PROMPT = """אתה שופט איכות של מערכת אחזור (retrieval) למסמכי מיסוי בישראל.
מקבל שאלה ואת הקטעים שהמערכת אחזרה עבורה. אתה **לא** רואה את התשובה שניתנה, ואינך אמור לנחש אותה.

השאלה היחידה שלך: עד כמה הקטעים שאוחזרו רלוונטיים לשאלה?
good — לפחות קטע אחד מכיל ממש את המידע הדרוש למענה על השאלה.
ok   — הקטעים באותו תחום נושאי אך אף אחד לא מכיל את המידע הספציפי הנדרש.
bad  — הקטעים עוסקים בנושא אחר לגמרי."""


def judge_context_relevance(question: str, chunks: list[str]) -> CriterionVerdict:
    context = "\n\n---\n\n".join(f"[{i}] {c}" for i, c in enumerate(chunks, 1))
    return _judge(CONTEXT_RELEVANCE_PROMPT, f"שאלה: {question}\n\nקטעים שאוחזרו:\n{context}")


FAITHFULNESS_PROMPT = """אתה שופט ביסוס (faithfulness) של תשובה במקורות שסופקו לה.
מקבל שאלה, את הקטעים שעמדו לרשות המערכת, ואת התשובה. אתה **לא** רואה תשובת ייחוס, ואינך אמור לשפוט אם התשובה נכונה בעולם — רק אם היא נתמכת בקטעים.

good — כל טענה עובדתית בתשובה (מספר, שיעור, כלל, סעיף) נתמכת ישירות באחד הקטעים.
       **סירוב הוא good** כאשר הקטעים אינם מכילים את התשובה **לשאלה שנשאלה**. אל תדרג סירוב כ-bad
       רק משום שהקטעים עוסקים בנושא כללי דומה — בדוק אם הם עונים על השאלה הספציפית.
ok   — טענה אחת מנוסחת בקירוב/בהכללה ביחס לקטעים, אך אין המצאה ואין סתירה.
bad  — לפחות טענה אחת שאינה בקטעים כלל, או סותרת אותם; או סירוב למרות שהתשובה לשאלה כן נמצאת בקטעים."""


def judge_faithfulness(answer: str, chunks: list[str], question: str | None = None) -> CriterionVerdict:
    """question was originally withheld to prevent the judge reasoning backwards
    from it. That was the wrong call: the leakage risk lives in the reference
    answer, not the question, and without the question the judge cannot tell a
    correct refusal from an unfaithful one -- it scores the refusal against
    whatever the chunks happen to be about. Measured cost of the old version:
    both unanswerable rows scored `bad`, dragging hard-slice faithfulness from
    0.500 to 0.333. See assignment3_writeup.md."""
    context = "\n\n---\n\n".join(f"[{i}] {c}" for i, c in enumerate(chunks, 1))
    header = f"שאלה: {question}\n\n" if question else ""
    return _judge(FAITHFULNESS_PROMPT, f"{header}קטעים שסופקו:\n{context}\n\nהתשובה להערכה:\n{answer}")


ANSWER_RELEVANCE_PROMPT = """אתה שופט האם תשובה עונה על השאלה שנשאלה.
מקבל שאלה ותשובה בלבד. אל תשפוט נכונות עובדתית — רק האם זו תשובה לשאלה הזו.

good — התשובה מתייחסת ישירות למה שנשאל; סירוב מפורש ("לא מצאתי את זה במסמכים") נחשב good כשהוא ברור וממוקד.
ok   — התשובה נוגעת בנושא אך עונה חלקית או עוקפת חלק מהשאלה.
bad  — התשובה עוסקת במשהו אחר, או ריקה/חסרת תוכן."""


def judge_answer_relevance(question: str, answer: str) -> CriterionVerdict:
    return _judge(ANSWER_RELEVANCE_PROMPT, f"שאלה: {question}\n\nתשובה: {answer}")


CORRECTNESS_PROMPT = """אתה שופט נכונות עובדתית מול תשובת ייחוס שנכתבה בידי אדם.
מקבל שאלה, תשובת ייחוס, ותשובת המערכת.

good — תשובת המערכת תואמת עובדתית לתשובת הייחוס (מספרים/שיעורים/כללים זהים). ניסוח שונה אינו פוגם.
ok   — הכיוון נכון אך חסר פרט מהותי, או מספר מעוגל/מקורב.
bad  — סתירה עובדתית לתשובת הייחוס, מספר שגוי, או סירוב לענות כשתשובת הייחוס מכילה תשובה עניינית.

הערה: אם תשובת הייחוס עצמה אומרת שהמידע אינו במסמכים, אז סירוב של המערכת הוא good."""


def judge_correctness(question: str, answer: str, reference_answer: str) -> CriterionVerdict:
    return _judge(
        CORRECTNESS_PROMPT,
        f"שאלה: {question}\n\nתשובת ייחוס:\n{reference_answer}\n\nתשובת המערכת:\n{answer}",
    )


def _compute_judge_version(
    prompts: tuple[str, ...] = (
        CONTEXT_RELEVANCE_PROMPT,
        FAITHFULNESS_PROMPT,
        ANSWER_RELEVANCE_PROMPT,
        CORRECTNESS_PROMPT,
    ),
) -> str:
    """Derived, not hand-bumped: editing a judge prompt changes this value
    automatically, so there's no version number to remember to update.
    `prompts` defaults to the four real prompts but takes any tuple, which is
    what makes this testable without monkeypatching module globals."""
    joined = "\x00".join(prompts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:8]


JUDGE_VERSION = _compute_judge_version()


def refusal_correctness(answerable: bool, answered: bool) -> str:
    """Code-only. Both error directions are counted separately on purpose:
    a false answer on an unanswerable question is a different (worse) failure
    than a false refusal on an answerable one."""
    if not answerable:
        return "correct_refusal" if not answered else "false_answer"
    return "correct_answer" if answered else "false_refusal"


VERDICT_SCORE = {"good": 1.0, "ok": 0.5, "bad": 0.0}
