"""Shared LLM client helpers for api/agents/* (explainer.py, qa.py, judge.py).

Two providers: Gemini (via the openai-compatible endpoint) and Anthropic
(native SDK). call_text/call_structured dispatch between them by model name
prefix (_is_anthropic_model) so callers never need to know which provider a
given model string belongs to -- qa.py/judge.py are unchanged by this."""

import json
import os
import re
import time
from dataclasses import dataclass
from typing import TypeVar

import anthropic
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

load_dotenv()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Anthropic model ids are all "claude-*" (e.g. claude-haiku-4-5); Gemini ids
# are all "gemini-*" -- no collision risk between the two namespaces.
ANTHROPIC_MODEL_PREFIX = "claude-"

# messages.create() truncated a real run mid-sentence once at the default
# ceiling (see src/agent_team.py's CODIFY note) -- same fixed budget here.
ANTHROPIC_MAX_TOKENS = 8192

_client: OpenAI | None = None
_anthropic_client: anthropic.Anthropic | None = None


def _get_client() -> OpenAI:
    """Built lazily on first real call, not at import time -- importing this
    module (or explainer.py/qa.py/judge.py) must not require GEMINI_API_KEY
    to be set."""
    global _client
    if _client is None:
        _client = OpenAI(base_url=GEMINI_BASE_URL, api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _get_anthropic_client() -> anthropic.Anthropic:
    """Lazy for the same reason as _get_client() -- see src/agent_team.py's
    get_anthropic_client(), the proven reference for this call pattern. No
    truststore.inject_into_ssl() here: that workaround was needed only for
    the openai/httpx client hitting this network's TLS-inspecting proxy: the
    Anthropic SDK's own httpx2 already trusts the OS store (see root
    CLAUDE.md CODIFY 2026-08-23)."""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _anthropic_client


def _is_anthropic_model(model: str) -> bool:
    return model.startswith(ANTHROPIC_MODEL_PREFIX)


class AgentCallError(Exception):
    """Raised when an LLM call still fails after all retries are exhausted.
    Callers (eventually the API layer) catch this to degrade gracefully
    (e.g. write llm_calls.error) instead of it propagating as a raw SDK
    exception."""


_FENCE_RE = re.compile(r"^```(json)?|```$", re.MULTILINE)


def strip_code_fence(raw: str) -> str:
    """Gemini sometimes wraps JSON in a ```` ```json ... ``` ```` fence even
    when asked for "JSON only" -- same fix as assignment2_judge.py."""
    return _FENCE_RE.sub("", raw).strip()


@dataclass(frozen=True)
class TextCallResult:
    text: str
    latency_ms: float
    input_tokens: int
    output_tokens: int


def call_text(
    *,
    model: str,
    system_prompt: str,
    user_content: str,
    temperature: float,
    max_retries: int = 2,
) -> TextCallResult:
    """Free-text completion. Dispatches to Gemini or Anthropic by model name."""
    if _is_anthropic_model(model):
        return _call_text_anthropic(
            model=model,
            system_prompt=system_prompt,
            user_content=user_content,
            max_retries=max_retries,
        )
    return _call_text_gemini(
        model=model,
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=temperature,
        max_retries=max_retries,
    )


def _call_text_gemini(
    *,
    model: str,
    system_prompt: str,
    user_content: str,
    temperature: float,
    max_retries: int = 2,
) -> TextCallResult:
    """Retries on RateLimitError only (short, capped)."""
    client = _get_client()
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            start = time.perf_counter()
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            usage = response.usage
            return TextCallResult(
                text=response.choices[0].message.content or "",
                latency_ms=latency_ms,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            )
        except RateLimitError as e:
            last_error = e
            if attempt == max_retries:
                break
            time.sleep(2 * (attempt + 1))
    raise AgentCallError(
        f"Gemini call failed after {max_retries + 1} attempt(s): {last_error}"
    ) from last_error


def _call_text_anthropic(
    *,
    model: str,
    system_prompt: str,
    user_content: str,
    max_retries: int = 2,
) -> TextCallResult:
    """Retries on RateLimitError only, same shape as _call_text_gemini.

    No temperature param: messages.create() on the installed SDK (1.0.0) has
    no top-level temperature/sampling knob (confirmed against the installed
    package -- OutputConfigParam only carries effort/format), matching
    src/agent_team.py's call, which already omits it."""
    client = _get_anthropic_client()
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            start = time.perf_counter()
            response = client.messages.create(
                model=model,
                max_tokens=ANTHROPIC_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            latency_ms = (time.perf_counter() - start) * 1000
            text = "".join(block.text for block in response.content if block.type == "text")
            usage = response.usage
            return TextCallResult(
                text=text,
                latency_ms=latency_ms,
                input_tokens=usage.input_tokens if usage else 0,
                output_tokens=usage.output_tokens if usage else 0,
            )
        except anthropic.RateLimitError as e:
            last_error = e
            if attempt == max_retries:
                break
            time.sleep(2 * (attempt + 1))
    raise AgentCallError(
        f"Anthropic call failed after {max_retries + 1} attempt(s): {last_error}"
    ) from last_error


ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True)
class StructuredCallResult:
    parsed: BaseModel
    latency_ms: float
    input_tokens: int
    output_tokens: int


def call_structured(
    *,
    model: str,
    system_prompt: str,
    user_content: str,
    temperature: float,
    response_model: type[ModelT],
    max_retries: int = 2,
) -> StructuredCallResult:
    """Pydantic-validated completion. Dispatches to Gemini or Anthropic by
    model name."""
    if _is_anthropic_model(model):
        return _call_structured_anthropic(
            model=model,
            system_prompt=system_prompt,
            user_content=user_content,
            response_model=response_model,
            max_retries=max_retries,
        )
    return _call_structured_gemini(
        model=model,
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=temperature,
        response_model=response_model,
        max_retries=max_retries,
    )


def _call_structured_gemini(
    *,
    model: str,
    system_prompt: str,
    user_content: str,
    temperature: float,
    response_model: type[ModelT],
    max_retries: int = 2,
) -> StructuredCallResult:
    """Strips code fences before parsing, then retries on RateLimitError
    (quota -- backs off a few seconds) or malformed output
    (ValidationError/json.JSONDecodeError -- backs off briefly, since asking
    again usually just fixes formatting)."""
    client = _get_client()
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            start = time.perf_counter()
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            raw = strip_code_fence((response.choices[0].message.content or "").strip())
            parsed = response_model.model_validate_json(raw)
            usage = response.usage
            return StructuredCallResult(
                parsed=parsed,
                latency_ms=latency_ms,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            )
        except RateLimitError as e:
            last_error = e
            if attempt == max_retries:
                break
            time.sleep(3 * (attempt + 1))
        except (ValidationError, json.JSONDecodeError) as e:
            last_error = e
            if attempt == max_retries:
                break
            time.sleep(1)
    raise AgentCallError(
        f"Gemini structured call failed after {max_retries + 1} attempt(s): {last_error}"
    ) from last_error


def _call_structured_anthropic(
    *,
    model: str,
    system_prompt: str,
    user_content: str,
    response_model: type[ModelT],
    max_retries: int = 2,
) -> StructuredCallResult:
    """Same retry/fence-stripping shape as _call_structured_gemini. No
    temperature param -- see _call_text_anthropic's docstring."""
    client = _get_anthropic_client()
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            start = time.perf_counter()
            response = client.messages.create(
                model=model,
                max_tokens=ANTHROPIC_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            latency_ms = (time.perf_counter() - start) * 1000
            text = "".join(block.text for block in response.content if block.type == "text")
            raw = strip_code_fence(text.strip())
            parsed = response_model.model_validate_json(raw)
            usage = response.usage
            return StructuredCallResult(
                parsed=parsed,
                latency_ms=latency_ms,
                input_tokens=usage.input_tokens if usage else 0,
                output_tokens=usage.output_tokens if usage else 0,
            )
        except anthropic.RateLimitError as e:
            last_error = e
            if attempt == max_retries:
                break
            time.sleep(3 * (attempt + 1))
        except (ValidationError, json.JSONDecodeError) as e:
            last_error = e
            if attempt == max_retries:
                break
            time.sleep(1)
    raise AgentCallError(
        f"Anthropic structured call failed after {max_retries + 1} attempt(s): {last_error}"
    ) from last_error
