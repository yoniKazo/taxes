"""Agent: explainer -- explains a computed tax result in plain Hebrew.

Used by POST /calculate (per plan decision #3, always with the agent's DB
defaults there -- overrides only ever flow through the Test Lab).
"""

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
    """context is a pre-built Hebrew string describing a computed tax result
    (combined gross, job count, tax before/after credit, national insurance,
    health tax, net, pension/keren-hishtalmut savings, donation credit) --
    the caller builds it, this function just sends it.

    model/system_prompt/temperature are required-but-nullable pass-throughs:
    resolving None to the explainer agent's DB-stored defaults is the
    caller's job (the `agents` table), not this function's -- it does not
    hardcode any defaults itself.

    Output is deliberately free text, not JSON: it sidesteps the
    fence-stripping/parse-failure mode entirely, unlike hello_llm.py's
    structured-output habit.
    """
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
