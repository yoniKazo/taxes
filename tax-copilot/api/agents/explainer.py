"""Agent: explainer -- explains a computed tax result in plain Hebrew. Used by
POST /calculate."""

from dataclasses import dataclass

from api.agents.base import call_text


@dataclass(frozen=True)
class ExplainResult:
    text: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    model: str
    system_prompt: str
    temperature: float


def explain(
    context: str,
    *,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float | None = None,
) -> ExplainResult:
    """context is the pre-built Hebrew description of a computed tax result;
    caller resolves None model/system_prompt/temperature to the explainer
    agent's DB defaults."""
    result = call_text(
        model=model,
        system_prompt=system_prompt,
        user_content=context,
        temperature=temperature,
    )
    return ExplainResult(
        text=result.text,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
    )
