"""מטלה 4 -- בדיקות ל-dispatch של model_providers: claude-*/gemini-* בוחרים את
המחלקה/הנתיב הנכון, בלי לקרוא בפועל ל-API."""

import sys
from pathlib import Path

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from src.model_providers import build_chat_model, call_judge_structured  # noqa: E402


def test_build_chat_model_claude_prefix_returns_chat_anthropic():
    model = build_chat_model("claude-haiku-4-5")
    assert isinstance(model, ChatAnthropic)


def test_build_chat_model_gemini_prefix_returns_chat_google_genai():
    model = build_chat_model("gemini-flash-lite-latest")
    assert isinstance(model, ChatGoogleGenerativeAI)


def test_build_chat_model_unknown_prefix_raises():
    with pytest.raises(ValueError, match="לא ידוע"):
        build_chat_model("gpt-4o")


class _DummyVerdict(BaseModel):
    explanation: str
    verdict: str


def test_call_judge_structured_dispatches_claude_to_claude_call():
    calls = []

    def fake_claude_call(model, system_prompt, user_content, response_model):
        calls.append((model, system_prompt, user_content, response_model))
        return _DummyVerdict(explanation="ok", verdict="good")

    result = call_judge_structured("claude-sonnet-5", "sys", "user", _DummyVerdict, claude_call=fake_claude_call)
    assert result.verdict == "good"
    assert calls == [("claude-sonnet-5", "sys", "user", _DummyVerdict)]


def test_call_judge_structured_claude_without_claude_call_raises():
    with pytest.raises(ValueError, match="claude_call"):
        call_judge_structured("claude-sonnet-5", "sys", "user", _DummyVerdict)


def test_call_judge_structured_unknown_prefix_raises():
    with pytest.raises(ValueError, match="לא ידוע"):
        call_judge_structured("gpt-4o", "sys", "user", _DummyVerdict)
