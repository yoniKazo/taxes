"""T1 (specs/001-judge-version-stamping/tasks.md): failing-first tests for
judge_version stamping. No network -- call_structured is monkeypatched,
matching this repo's existing convention (see test_agents_unit.py).
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import pandas as pd
import pytest

import assignment3_evaluate
import judges
from judges import CriterionVerdict


def test_judge_version_is_deterministic():
    assert judges._compute_judge_version() == judges._compute_judge_version()


def test_judge_version_changes_with_prompt_text():
    a = judges._compute_judge_version(("a", "b", "c", "d"))
    b = judges._compute_judge_version(("a", "b", "c", "e"))
    assert a != b


def test_judge_version_is_short_hex():
    assert re.fullmatch(r"[0-9a-f]{8}", judges.JUDGE_VERSION)


@pytest.fixture
def fake_verdict(monkeypatch):
    verdict = CriterionVerdict(explanation="test", verdict="good")
    monkeypatch.setattr(judges, "call_structured", lambda *a, **k: (verdict, None))


def test_judge_rag_row_includes_judge_version(fake_verdict):
    row = pd.Series({
        "question": "שאלה",
        "retrieved_texts": ["קטע"],
        "rag_answer": "תשובה",
        "reference_answer": "תשובת ייחוס",
    })
    out = assignment3_evaluate.judge_rag_row(row)
    assert out["judge_version"] == judges.JUDGE_VERSION


def test_judge_baseline_row_includes_judge_version(fake_verdict):
    row = pd.Series({
        "question": "שאלה",
        "baseline_answer": "תשובה",
        "reference_answer": "תשובת ייחוס",
    })
    out = assignment3_evaluate.judge_baseline_row(row)
    assert out["judge_version"] == judges.JUDGE_VERSION
