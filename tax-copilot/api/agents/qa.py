"""Agent: qa -- grounded question answering over data/tax_notes.md (port of
src/file_qa.py's grounding rules)."""

from dataclasses import dataclass

from api.agents.base import call_text


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
    system_prompt: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
) -> AnswerResult:
    """document/question build the user message; system_prompt is the
    resolved grounding prompt (caller resolves DB defaults, e.g. via
    resolve_overrides)."""
    user_content = f"מסמך:\n{document}\n\nשאלה: {question}"
    result = call_text(
        model=model,
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=temperature,
    )
    return AnswerResult(
        text=result.text,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
    )
