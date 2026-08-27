"""מטלה 4 -- בדיקות ל-get_matrix_results(): שתי הבאגים האמיתיים שנתפסו ידנית
(TypeError על תא ריק מספרי, TypeError על assign ל-dtype לא-תואם, ואיבוד תוכן
אמיתי בעמודות שלא היו צריכות להתבלבל עם "n/a") לא יחזרו בשקט.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from api.agentlab import runner  # noqa: E402


@pytest.fixture
def synthetic_xlsx(tmp_path, monkeypatch):
    """שורה אחת "n/a" אמיתית (rag, no_tool) + שורה אחת רגילה (rag, single),
    בדיוק כמו assignment4_eval_runner.run_rag_row כותב אותן בפועל."""
    rows = [
        {
            "task_id": "nt1", "task": "מה אתה יכול לעזור לי איתו?", "type": "no_tool",
            "answerable": True, "success_criteria": "tool_calls == 0",
            "config": "rag", "run": 1, "answer": "n/a", "success": "n/a", "refused": "n/a",
            "terminal_state": "n/a", "tool_calls": 0, "tools_used": "[]", "steps": 0,
            "faithfulness_verdict": "n/a",
            "faithfulness_explanation": "structurally meaningless for RAG -- no tool concept",
            "latency_ms": None, "input_tokens": None, "output_tokens": None,
            "refusal_correctness": "n/a",
        },
        {
            "task_id": "s2", "task": "מהי תקרת הפטור?", "type": "single",
            "answerable": True, "success_criteria": 'answer contains "5,008,000"',
            "config": "rag", "run": 1, "answer": "5,008,000 ₪", "success": "good", "refused": False,
            "terminal_state": "answered", "tool_calls": 1, "tools_used": "['search_tax_corpus']", "steps": 1,
            "faithfulness_verdict": "good", "faithfulness_explanation": "נתמך במקור",
            "latency_ms": 1500.0, "input_tokens": 2000, "output_tokens": 100,
            "refusal_correctness": "correct_answer",
        },
    ]
    path = tmp_path / "assignment_04.xlsx"
    pd.DataFrame(rows).to_excel(path, index=False)
    monkeypatch.setattr(runner, "XLSX_PATH", str(path))
    return path


def test_get_matrix_results_never_raises_and_marks_na_rows(synthetic_xlsx):
    result = runner.get_matrix_results()
    assert result["available"] is True
    assert len(result["rows"]) == 2


def test_na_row_shows_literal_na_not_null(synthetic_xlsx):
    result = runner.get_matrix_results()
    nt1 = next(r for r in result["rows"] if r["task_id"] == "nt1")
    assert nt1["answer"] == "n/a"
    assert nt1["success"] == "n/a"
    assert nt1["terminal_state"] == "n/a"


def test_na_row_preserves_real_content_not_literally_na(synthetic_xlsx):
    """tools_used ("[]") ו-faithfulness_explanation (משפט אמיתי) לא נכתבו כ-"n/a"
    בפועל -- אסור שיוחלפו בו רק כי השורה structurally meaningless."""
    result = runner.get_matrix_results()
    nt1 = next(r for r in result["rows"] if r["task_id"] == "nt1")
    assert nt1["tools_used"] == "[]"
    assert "structurally meaningless" in nt1["faithfulness_explanation"]


def test_numeric_aggregation_does_not_crash_on_na_rows(synthetic_xlsx):
    """זו בדיוק השורה שקרסה בפועל: latency_ms ריק בשורת ה-n/a לא אמור לשבור .mean()."""
    result = runner.get_matrix_results()
    no_tool_summary = next(s for s in result["summary"] if s["type"] == "no_tool")
    assert no_tool_summary["mean_latency_ms"] is None
    single_summary = next(s for s in result["summary"] if s["type"] == "single")
    assert single_summary["mean_latency_ms"] == 1500.0


def test_missing_xlsx_returns_available_false(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "XLSX_PATH", str(tmp_path / "does_not_exist.xlsx"))
    result = runner.get_matrix_results()
    assert result == {"available": False, "rows": [], "summary": {}}
