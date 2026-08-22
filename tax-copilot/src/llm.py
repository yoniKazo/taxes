"""Shared Gemini client for the assignment 3 scripts.

Same pattern as assignment2_generate.py / assignment2_judge.py (see
.claude/skills/add-llm-script/), factored out because assignment 3 has five
callers instead of two: eval-set generation, the no-RAG baseline, the RAG
pipeline, four judges, and the experiment runner.

Throttling is not optional here -- .claude/rules/hosted-llm-quota.md: the free
tier allows 15 req/min on "-lite" checkpoints, and non-lite tiers are capped at
20 requests/DAY. Both models below are deliberately lite.
"""

import os
import re
import sys
import time
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

GENERATOR_MODEL = "gemini-flash-lite-latest"
# Different checkpoint from the generator, to reduce self-enhancement bias while
# staying inside the lite tier's 15/min quota (a non-lite judge would burn its
# 20/day cap on the first six rows).
JUDGE_MODEL = "gemini-3.1-flash-lite"

THROTTLE_SECONDS = 4
MAX_ATTEMPTS = 5
RATE_LIMIT_BACKOFF = 15

# Free tier allows 15 requests/minute. Callers that fire several calls per loop
# iteration (Task 5 judges four criteria per row) blow past that if throttling is
# left to the caller: four back-to-back calls plus one 4s sleep is ~24 req/min,
# which rate-limits, backs off 15s, retries, and turns a 12-minute run into 90.
# Enforcing the floor here makes the rule structural instead of a discipline
# every new caller has to remember.
MIN_SECONDS_BETWEEN_CALLS = 4.2
_last_call_at = 0.0

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_client: OpenAI | None = None


def get_client() -> OpenAI:
    """Built on first call, not at import.

    The FastAPI layer imports this module transitively just to read chunk
    metadata and eval-set CSVs -- work that costs zero calls. Constructing the
    client at import time made a missing GEMINI_API_KEY crash uvicorn at
    startup, and made the free half of the RAG feature untestable without a key.
    """
    global _client
    if _client is None:
        _client = OpenAI(base_url=BASE_URL, api_key=os.environ["GEMINI_API_KEY"])
    return _client


@dataclass(frozen=True)
class LLMResult:
    text: str
    latency_ms: float
    input_tokens: int
    output_tokens: int


def strip_code_fences(raw: str) -> str:
    """Gemini wraps JSON in markdown fences even when told not to."""
    return re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()


def repair_json_quotes(raw: str) -> str:
    """Escape gershayim that Gemini left raw inside JSON string values.

    Hebrew tax terms are written with an ASCII double quote (מע"מ, בע"מ, דו"ח),
    and Gemini escapes them in some fields while emitting them raw in others --
    within the same response. response_format={"type":"json_object"} does not
    fix it. Heuristic: inside a string, a quote only closes it if the next
    non-space character is structural (: , } ]); otherwise it is literal.
    """
    out: list[str] = []
    in_string = False
    i = 0
    while i < len(raw):
        char = raw[i]
        if not in_string:
            out.append(char)
            in_string = char == '"'
        elif char == "\\":
            out.append(raw[i:i + 2])
            i += 2
            continue
        elif char == '"':
            nxt = i + 1
            while nxt < len(raw) and raw[nxt] in " \t\r\n":
                nxt += 1
            if nxt < len(raw) and raw[nxt] in ":,}]":
                out.append(char)
                in_string = False
            else:
                out.append('\\"')
        else:
            out.append(char)
        i += 1
    return "".join(out)


def _wait_for_slot() -> None:
    """Block until MIN_SECONDS_BETWEEN_CALLS have passed since the last request."""
    global _last_call_at
    wait = MIN_SECONDS_BETWEEN_CALLS - (time.monotonic() - _last_call_at)
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.monotonic()


def call_text(system_prompt: str, user_content: str, *, model: str = GENERATOR_MODEL,
              temperature: float | None = None, json_mode: bool = False) -> LLMResult:
    kwargs = {} if temperature is None else {"temperature": temperature}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    for attempt in range(MAX_ATTEMPTS):
        try:
            _wait_for_slot()
            start = time.perf_counter()
            response = get_client().chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                **kwargs,
            )
            return LLMResult(
                text=response.choices[0].message.content.strip(),
                latency_ms=round((time.perf_counter() - start) * 1000, 1),
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )
        except RateLimitError:
            if attempt == MAX_ATTEMPTS - 1:
                raise
            time.sleep(RATE_LIMIT_BACKOFF)


def call_structured[T: BaseModel](system_prompt: str, user_content: str, response_model: type[T],
                                  *, model: str = GENERATOR_MODEL,
                                  temperature: float | None = None) -> tuple[T, LLMResult]:
    """json_mode is not optional here: Hebrew tax prose is full of gershayim
    (מע"מ, בע"מ, דו"ח), and in free-text mode Gemini emits them raw inside JSON
    strings, which breaks the parse on exactly those rows. Asking the API for a
    JSON object makes it escape them properly."""
    for attempt in range(MAX_ATTEMPTS):
        result = call_text(system_prompt, user_content, model=model,
                           temperature=temperature, json_mode=True)
        cleaned = strip_code_fences(result.text)
        for candidate in (cleaned, repair_json_quotes(cleaned)):
            try:
                return response_model.model_validate_json(candidate), result
            except ValidationError as e:
                last_error = e
        if attempt == MAX_ATTEMPTS - 1:
            raise last_error
        print(f"  (retry: malformed structured output: {str(last_error)[:120]})")
        time.sleep(2)


def throttle(i: int) -> None:
    """Kept for the assignment-2-era call sites. Pacing is now enforced inside
    call_text via _wait_for_slot(), so this is a no-op that stays only so the
    existing loops read the same as before."""
