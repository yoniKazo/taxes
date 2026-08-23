"""X4: tests for the Gemini-workers / Anthropic-lead team in src/agent_team.py.
No network -- both call_structured (Gemini) and the Anthropic client are
monkeypatched, matching this repo's existing convention (see
test_judge_version.py, test_agents_unit.py).
"""

import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import pytest

import agent_team
from agent_team import ProviderUsage, UnsourcedFigure, WorkerReport


MANIFEST = [
    {"doc_name": "doc-a", "path": "TaxData/a.md", "format": "md"},
    {"doc_name": "doc-b", "path": "TaxData/b.md", "format": "md"},
]


class _FakeLLMResult:
    def __init__(self, input_tokens: int = 100, output_tokens: int = 50, latency_ms: float = 12.3) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.latency_ms = latency_ms


def _report_for(doc_name: str, n_findings: int = 1) -> WorkerReport:
    figures = [UnsourcedFigure(figure=f"{doc_name}-figure-{i}", location="section") for i in range(n_findings)]
    return WorkerReport(doc_name=doc_name, unsourced_figures=figures)


@pytest.fixture(autouse=True)
def no_real_files(monkeypatch):
    monkeypatch.setattr(agent_team, "_read_document_text", lambda doc: f"text for {doc['doc_name']}")


# --- run_workers ---


def test_run_workers_returns_one_result_per_document(monkeypatch):
    monkeypatch.setattr(agent_team, "call_structured",
                         lambda *a, **k: (_report_for("doc-a"), _FakeLLMResult()))

    results = agent_team.run_workers(MANIFEST)

    assert {r.doc_name for r in results} == {"doc-a", "doc-b"}
    assert all(r.report is not None and r.error is None for r in results)
    assert all(r.usage.provider == "gemini" for r in results)


def test_run_workers_survives_a_failing_worker(monkeypatch):
    def fake_call_structured(system_prompt, user_content, response_model):
        if "doc-b" in user_content:
            raise ValueError("Gemini blew up")
        return _report_for("doc-a"), _FakeLLMResult()

    monkeypatch.setattr(agent_team, "call_structured", fake_call_structured)

    results = agent_team.run_workers(MANIFEST)
    by_name = {r.doc_name: r for r in results}

    assert by_name["doc-a"].report is not None
    assert by_name["doc-b"].report is None
    assert "blew up" in by_name["doc-b"].error


# --- merge_reports (the one Anthropic call) ---


class _FakeTextBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _FakeAnthropicMessages:
    def __init__(self, reply_text: str, input_tokens: int, output_tokens: int) -> None:
        self._reply_text = reply_text
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self.call_count = 0

    def create(self, **kwargs):
        self.call_count += 1
        return SimpleNamespace(
            content=[_FakeTextBlock(self._reply_text)],
            usage=SimpleNamespace(input_tokens=self._input_tokens, output_tokens=self._output_tokens),
        )


class _FakeAnthropicClient:
    def __init__(self, reply_text: str = "# דוח ממוזג", input_tokens: int = 200, output_tokens: int = 80) -> None:
        self.messages = _FakeAnthropicMessages(reply_text, input_tokens, output_tokens)


def test_merge_reports_makes_exactly_one_anthropic_call(monkeypatch):
    fake_client = _FakeAnthropicClient(reply_text="# סיכום")
    monkeypatch.setattr(agent_team, "get_anthropic_client", lambda: fake_client)

    worker_results = [
        agent_team.WorkerResult(doc_name="doc-a", report=_report_for("doc-a"), usage=None),
        agent_team.WorkerResult(doc_name="doc-b", report=None, usage=None, error="failed"),
    ]

    text, usage = agent_team.merge_reports(worker_results)

    assert text == "# סיכום"
    assert fake_client.messages.call_count == 1
    assert usage.provider == "anthropic"
    assert usage.model == agent_team.LEAD_MODEL
    assert usage.input_tokens == 200
    assert usage.output_tokens == 80


def test_merge_reports_mentions_failed_documents(monkeypatch):
    captured = {}

    def fake_create(**kwargs):
        captured["user_content"] = kwargs["messages"][0]["content"]
        return SimpleNamespace(
            content=[_FakeTextBlock("ok")],
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        )

    fake_client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))
    monkeypatch.setattr(agent_team, "get_anthropic_client", lambda: fake_client)

    worker_results = [agent_team.WorkerResult(doc_name="doc-b", report=None, usage=None, error="failed")]
    agent_team.merge_reports(worker_results)

    assert "doc-b" in captured["user_content"]


# --- ProviderUsage.cost_usd ---


def test_gemini_usage_is_free():
    usage = ProviderUsage(provider="gemini", model="gemini-flash-lite-latest",
                           input_tokens=10_000, output_tokens=10_000, latency_ms=1.0)
    assert usage.cost_usd == 0.0


def test_anthropic_haiku_cost_matches_pricing_table():
    usage = ProviderUsage(provider="anthropic", model="claude-haiku-4-5",
                           input_tokens=1_000_000, output_tokens=1_000_000, latency_ms=1.0)
    assert usage.cost_usd == pytest.approx(1.0 + 5.0)


# --- run_team (end to end, still fully mocked) ---


def test_run_team_end_to_end(monkeypatch):
    monkeypatch.setattr(agent_team, "call_structured",
                         lambda *a, **k: (_report_for("doc-a"), _FakeLLMResult()))
    fake_client = _FakeAnthropicClient(reply_text="# דוח סופי")
    monkeypatch.setattr(agent_team, "get_anthropic_client", lambda: fake_client)

    result = agent_team.run_team(manifest=MANIFEST)

    assert result.report_markdown == "# דוח סופי"
    assert len(result.worker_results) == 2
    assert result.lead_usage.provider == "anthropic"
    assert fake_client.messages.call_count == 1
