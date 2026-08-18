"""Shared Gemini client helper for api/agents/* (explainer.py, qa.py, judge.py)."""

import json
import os
import re
import time
from dataclasses import dataclass
from typing import TypeVar

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

load_dotenv()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Built lazily on first real call, not at import time -- importing this
    module (or explainer.py/qa.py/judge.py) must not require GEMINI_API_KEY
    to be set."""
    global _client
    if _client is None:
        _client = OpenAI(base_url=GEMINI_BASE_URL, api_key=os.environ["GEMINI_API_KEY"])
    return _client


class AgentCallError(Exception):
    """Raised when a Gemini call still fails after all retries are exhausted.
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
    """Free-text completion. Retries on RateLimitError only (short, capped)."""
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
    """Pydantic-validated completion. Strips code fences before parsing, then
    retries on RateLimitError (quota -- backs off a few seconds) or malformed
    output (ValidationError/json.JSONDecodeError -- backs off briefly, since
    asking again usually just fixes formatting)."""
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
