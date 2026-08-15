"""Unit tests for api/agents/base.py's pure logic -- fence-stripping and
retry-on-RateLimitError/ValidationError -- with a fake OpenAI client. No real
network call (quota risk with the hosted Gemini API is why this is mocked
instead of hitting the live endpoint)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import pytest
from openai import RateLimitError
from pydantic import BaseModel

from api.agents import base


def _rate_limit_error() -> RateLimitError:
    response = httpx.Response(status_code=429, request=httpx.Request("POST", "https://example.com"))
    return RateLimitError("rate limited", response=response, body=None)


class _FakeUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str, prompt_tokens: int = 10, completion_tokens: int = 5) -> None:
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage(prompt_tokens, completion_tokens)


class _FakeCompletions:
    def __init__(self, side_effects: list) -> None:
        self._side_effects = list(side_effects)
        self.call_count = 0

    def create(self, **kwargs):
        self.call_count += 1
        effect = self._side_effects.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect


class _FakeClient:
    """Mimics OpenAI(...).chat.completions.create(...) just enough for base.py."""

    def __init__(self, side_effects: list) -> None:
        completions = _FakeCompletions(side_effects)
        self.chat = type("_Chat", (), {"completions": completions})()


# --- strip_code_fence ---


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('```json\n{"a": 1}\n```', '{"a": 1}'),
        ('```\n{"a": 1}\n```', '{"a": 1}'),
        ('{"a": 1}', '{"a": 1}'),
    ],
)
def test_strip_code_fence(raw, expected):
    assert base.strip_code_fence(raw) == expected


# --- call_text: retry on RateLimitError ---


def test_call_text_retries_then_succeeds(monkeypatch):
    fake_client = _FakeClient([_rate_limit_error(), _FakeResponse("hello")])
    monkeypatch.setattr(base, "_get_client", lambda: fake_client)
    monkeypatch.setattr(base.time, "sleep", lambda _: None)

    result = base.call_text(
        model="gemini-flash-lite-latest",
        system_prompt="sys",
        user_content="hi",
        temperature=0.5,
    )

    assert result.text == "hello"
    assert result.input_tokens == 10
    assert result.output_tokens == 5
    assert fake_client.chat.completions.call_count == 2


def test_call_text_raises_after_retries_exhausted(monkeypatch):
    fake_client = _FakeClient([_rate_limit_error(), _rate_limit_error(), _rate_limit_error()])
    monkeypatch.setattr(base, "_get_client", lambda: fake_client)
    monkeypatch.setattr(base.time, "sleep", lambda _: None)

    with pytest.raises(base.AgentCallError):
        base.call_text(
            model="gemini-flash-lite-latest",
            system_prompt="sys",
            user_content="hi",
            temperature=0.5,
            max_retries=2,
        )

    assert fake_client.chat.completions.call_count == 3


# --- call_structured: fence-stripping + retry on ValidationError ---


class _Answer(BaseModel):
    text: str


def test_call_structured_strips_fence_and_parses(monkeypatch):
    fake_client = _FakeClient([_FakeResponse('```json\n{"text": "ok"}\n```')])
    monkeypatch.setattr(base, "_get_client", lambda: fake_client)

    result = base.call_structured(
        model="gemini-3.1-flash-lite",
        system_prompt="sys",
        user_content="hi",
        temperature=0.0,
        response_model=_Answer,
    )

    assert result.parsed == _Answer(text="ok")


def test_call_structured_retries_on_validation_error(monkeypatch):
    fake_client = _FakeClient([_FakeResponse("not json at all"), _FakeResponse('{"text": "ok"}')])
    monkeypatch.setattr(base, "_get_client", lambda: fake_client)
    monkeypatch.setattr(base.time, "sleep", lambda _: None)

    result = base.call_structured(
        model="gemini-3.1-flash-lite",
        system_prompt="sys",
        user_content="hi",
        temperature=0.0,
        response_model=_Answer,
    )

    assert result.parsed == _Answer(text="ok")
    assert fake_client.chat.completions.call_count == 2
