"""Unit tests for api/agents/base.py's pure logic -- fence-stripping and
retry-on-RateLimitError/ValidationError -- with a fake OpenAI client. No real
network call (quota risk with the hosted Gemini API is why this is mocked
instead of hitting the live endpoint)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import httpx2
import pytest
from anthropic import RateLimitError as AnthropicRateLimitError
from openai import RateLimitError
from pydantic import BaseModel

from api.agents import base


def _rate_limit_error() -> RateLimitError:
    response = httpx.Response(status_code=429, request=httpx.Request("POST", "https://example.com"))
    return RateLimitError("rate limited", response=response, body=None)


def _anthropic_rate_limit_error() -> AnthropicRateLimitError:
    # Anthropic's SDK ships its own httpx fork (httpx2) with a distinct
    # Response/Request type -- a plain httpx.Response doesn't satisfy it.
    response = httpx2.Response(status_code=429, request=httpx2.Request("POST", "https://example.com"))
    return AnthropicRateLimitError("rate limited", response=response, body=None)


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


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeAnthropicUsage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeAnthropicMessage:
    def __init__(self, text: str, input_tokens: int = 10, output_tokens: int = 5) -> None:
        self.content = [_FakeTextBlock(text)]
        self.usage = _FakeAnthropicUsage(input_tokens, output_tokens)


class _FakeAnthropicMessages:
    def __init__(self, side_effects: list) -> None:
        self._side_effects = list(side_effects)
        self.call_count = 0

    def create(self, **kwargs):
        self.call_count += 1
        # The installed SDK's messages.create() has no top-level temperature
        # param (confirmed against anthropic==1.0.0) -- a regression that
        # re-adds it would fail for real, not just in this fake.
        assert "temperature" not in kwargs
        effect = self._side_effects.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect


class _FakeAnthropicClient:
    """Mimics Anthropic(...).messages.create(...) just enough for base.py."""

    def __init__(self, side_effects: list) -> None:
        self.messages = _FakeAnthropicMessages(side_effects)


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


# --- Anthropic dispatch: call_text/call_structured route "claude-*" models
# to the Anthropic client instead of Gemini's, per _is_anthropic_model ---


def test_call_text_dispatches_to_anthropic_for_claude_model(monkeypatch):
    fake_client = _FakeAnthropicClient([_FakeAnthropicMessage("hello", input_tokens=7, output_tokens=3)])
    monkeypatch.setattr(base, "_get_anthropic_client", lambda: fake_client)

    result = base.call_text(
        model="claude-haiku-4-5",
        system_prompt="sys",
        user_content="hi",
        temperature=0.5,
    )

    assert result.text == "hello"
    assert result.input_tokens == 7
    assert result.output_tokens == 3
    assert fake_client.messages.call_count == 1


def test_call_text_anthropic_retries_then_succeeds(monkeypatch):
    fake_client = _FakeAnthropicClient([_anthropic_rate_limit_error(), _FakeAnthropicMessage("hello")])
    monkeypatch.setattr(base, "_get_anthropic_client", lambda: fake_client)
    monkeypatch.setattr(base.time, "sleep", lambda _: None)

    result = base.call_text(
        model="claude-haiku-4-5",
        system_prompt="sys",
        user_content="hi",
        temperature=0.5,
    )

    assert result.text == "hello"
    assert fake_client.messages.call_count == 2


def test_call_text_anthropic_raises_after_retries_exhausted(monkeypatch):
    fake_client = _FakeAnthropicClient(
        [_anthropic_rate_limit_error(), _anthropic_rate_limit_error(), _anthropic_rate_limit_error()]
    )
    monkeypatch.setattr(base, "_get_anthropic_client", lambda: fake_client)
    monkeypatch.setattr(base.time, "sleep", lambda _: None)

    with pytest.raises(base.AgentCallError):
        base.call_text(
            model="claude-haiku-4-5",
            system_prompt="sys",
            user_content="hi",
            temperature=0.5,
            max_retries=2,
        )

    assert fake_client.messages.call_count == 3


def test_call_structured_anthropic_strips_fence_and_parses(monkeypatch):
    fake_client = _FakeAnthropicClient([_FakeAnthropicMessage('```json\n{"text": "ok"}\n```')])
    monkeypatch.setattr(base, "_get_anthropic_client", lambda: fake_client)

    result = base.call_structured(
        model="claude-haiku-4-5",
        system_prompt="sys",
        user_content="hi",
        temperature=0.0,
        response_model=_Answer,
    )

    assert result.parsed == _Answer(text="ok")


def test_call_structured_anthropic_retries_on_validation_error(monkeypatch):
    fake_client = _FakeAnthropicClient(
        [_FakeAnthropicMessage("not json at all"), _FakeAnthropicMessage('{"text": "ok"}')]
    )
    monkeypatch.setattr(base, "_get_anthropic_client", lambda: fake_client)
    monkeypatch.setattr(base.time, "sleep", lambda _: None)

    result = base.call_structured(
        model="claude-haiku-4-5",
        system_prompt="sys",
        user_content="hi",
        temperature=0.0,
        response_model=_Answer,
    )

    assert result.parsed == _Answer(text="ok")
    assert fake_client.messages.call_count == 2
