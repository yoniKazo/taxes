"""Agent: judge -- applies a rubric to a qa answer, grounded in the same
document, returning explanation+verdict per criterion. rubric_text is passed
in by the caller (from DB rubric_criteria rows), so editing the rubric via
RubricPanel changes what the judge applies. Latency is rated programmatically
elsewhere (api/scoring.py), never sent to the judge."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from api.agents.base import call_structured

Verdict = Literal["good", "ok", "bad"]


class CriterionVerdict(BaseModel):
    explanation: str
    verdict: Verdict


class JudgeOutput(BaseModel):
    fluency: CriterionVerdict
    grammar: CriterionVerdict
    tone: CriterionVerdict
    length: CriterionVerdict
    grounding: CriterionVerdict


def _build_system_prompt(rubric_text: str) -> str:
    return f"""אתה שופט איכות (LLM judge) שמעריך תשובות של בוט שאלות-תשובות על מיסוי שכירים בישראל.
החל את הרוברייק הבאה *במדויק* כפי שהיא מנוסחת -- אל תשתמש בסטנדרטים משלך:
{rubric_text}

לכל אחד מ-5 הקריטריונים (fluency, grammar, tone, length, grounding) החזר `explanation` (הסבר קצר לפסיקה, בעברית) ולפני זה נמק במדויק לפי הרוברייק, ואז `verdict` (good/ok/bad).
לצורך grounding, המקור היחיד המותר הוא המסמך המצורף -- לא ידע עולם, לא מה שאתה "יודע" על מיסוי ישראלי.
החזר אך ורק JSON תקני בפורמט הבא, ללא טקסט נוסף, ללא code fences:
{{"fluency": {{"explanation": "...", "verdict": "good|ok|bad"}}, "grammar": {{...}}, "tone": {{...}}, "length": {{...}}, "grounding": {{...}}}}"""


@dataclass(frozen=True)
class JudgeResult:
    output: JudgeOutput
    latency_ms: float
    input_tokens: int
    output_tokens: int
    model: str
    system_prompt: str
    temperature: float


def judge_answer(
    document: str,
    question: str,
    answer: str,
    rubric_text: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
) -> JudgeResult:
    """document/question/answer describe the qa call being judged; rubric_text
    is the active rubric's criteria text. No system_prompt param -- it's
    always built from the fixed judge persona + rubric_text."""
    system_prompt = _build_system_prompt(rubric_text)
    user_content = f"מסמך:\n{document}\n\nשאלה: {question}\n\nתשובת הבוט להערכה: {answer}"
    result = call_structured(
        model=model,
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=temperature,
        response_model=JudgeOutput,
    )
    return JudgeResult(
        output=result.parsed,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
    )
