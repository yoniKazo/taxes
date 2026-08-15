"""Agent: judge -- applies a rubric to a qa answer, grounded in the same
document, returning explanation+verdict per criterion.

Direct port of src/assignment2_judge.py's JudgeOutput schema and
system-prompt structure, EXCEPT the rubric text is a parameter built by the
caller from DB rubric_criteria rows (RUBRIC_TEXT there was a hardcoded
module constant; here it's `rubric_text`, a function argument) -- so editing
the rubric via the UI's RubricPanel actually changes what the judge applies.

Latency is never sent to the judge -- callers derive its rating
programmatically from latency_ms, same as assignment2_judge.py's
latency_rating()/compute_final_score(); that logic lives in api/scoring.py,
not here.
"""

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
    """document/question/answer describe the qa call being judged (the
    "graded" llm_calls row); rubric_text is the active rubric's criteria
    text, built by the caller from DB rows.

    model/temperature are required-but-nullable pass-throughs like the other
    two agents; per plan decision, /test-runs/{id}/judge in v1 doesn't
    actually override them (always the judge agent's DB defaults), but the
    parameters exist for consistency/future use.

    system_prompt is NOT a parameter here -- it's always built from the
    fixed judge persona + the passed-in rubric_text, so callers can't
    accidentally bypass the rubric.
    """
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
