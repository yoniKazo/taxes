"""Agent: qa -- grounded question answering over data/tax_notes.md.

Port of src/file_qa.py's grounding rules (answer only from the attached
document, quote the supporting passage, refuse with a fixed Hebrew sentence
if the document doesn't cover it). This is the agent the Test Lab evaluates
against the existing 24-question dataset (per plan section "Context").
"""

from dataclasses import dataclass

from api.agents.base import call_text

# Ported verbatim from src/file_qa.py. Used only as a fallback when the
# caller doesn't supply an override -- callers (routes/test_runs.py,
# routes/calculate.py's qa usage) are expected to pass the agent's DB-stored
# default/override system_prompt explicitly, same pattern as explainer.py.
DEFAULT_SYSTEM_PROMPT = """ענה אך ורק לפי המסמך המצורף. אל תשתמש בידע חיצוני ואל תנחש.
כאשר אתה עונה, צטט את הקטע המדויק מהמסמך שתומך בתשובה.
אם התשובה אינה מופיעה במסמך, השב אך ורק במשפט: "לא מצאתי את זה במסמך."""


@dataclass(frozen=True)
class AnswerResult:
    text: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    model: str
    system_prompt: str
    temperature: float


def answer(
    document: str,
    question: str,
    *,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float | None = None,
) -> AnswerResult:
    """document is the full contents of data/tax_notes.md (or equivalent),
    question is the user's question -- both go into the user message.

    model/temperature are required-but-nullable pass-throughs, same contract
    as explainer.explain(): resolving None to the qa agent's DB defaults is
    the caller's job. system_prompt falls back to DEFAULT_SYSTEM_PROMPT
    (file_qa.py's grounding rules) only if the caller doesn't supply one.
    """
    resolved_prompt = system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT
    user_content = f"מסמך:\n{document}\n\nשאלה: {question}"
    result = call_text(
        model=model,
        system_prompt=resolved_prompt,
        user_content=user_content,
        temperature=temperature,
    )
    return AnswerResult(
        text=result.text,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        model=model,
        system_prompt=resolved_prompt,
        temperature=temperature,
    )
