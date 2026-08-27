"""מטלה 4, Task 5 -- בדיקות ל-score_task_success (בדיקת-קוד מול success_criteria,
בלי קריאות LLM/API) ול-refusal_correctness (קוד בלבד)."""

import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from src.assignment4_eval_runner import score_task_success  # noqa: E402
from src.assignment4_judges import refusal_correctness  # noqa: E402


def _row(success_criteria: str) -> pd.Series:
    return pd.Series({"task": "שאלת בדיקה", "success_criteria": success_criteria})


def test_tool_calls_equals_zero_criterion():
    row = _row("tool_calls == 0")
    verdict, _ = score_task_success(row, answer="שלום!", tool_calls=0, terminal_state="answered")
    assert verdict == "good"
    verdict, _ = score_task_success(row, answer="שלום!", tool_calls=1, terminal_state="answered")
    assert verdict == "bad"


def test_refused_true_criterion():
    row = _row("refused == True")
    verdict, _ = score_task_success(row, answer="לא מצאתי", tool_calls=2, terminal_state="refused")
    assert verdict == "good"
    verdict, _ = score_task_success(row, answer="התשובה היא...", tool_calls=1, terminal_state="answered")
    assert verdict == "bad"


def test_refused_true_with_tool_calls_bound():
    row = _row("refused == True and tool_calls <= 2")
    verdict, _ = score_task_success(row, answer="לא מצאתי", tool_calls=2, terminal_state="refused")
    assert verdict == "good"
    verdict, _ = score_task_success(row, answer="לא מצאתי", tool_calls=5, terminal_state="refused")
    assert verdict == "bad", "חיפוש לא-חסום (5 קריאות) לא אמור לעבור למרות סירוב נכון"


def test_answer_contains_criterion_matches_either_quoted_form():
    row = _row('answer contains "320,000" or "320000" (±1)')
    assert score_task_success(row, answer="התשובה היא 320,000 ₪", tool_calls=2, terminal_state="answered")[0] == "good"
    assert score_task_success(row, answer="התשובה היא 320000 ₪", tool_calls=2, terminal_state="answered")[0] == "good"
    assert score_task_success(row, answer="התשובה היא 999,000 ₪", tool_calls=2, terminal_state="answered")[0] == "bad"


def test_answer_contains_tolerates_trailing_zero():
    row = _row('answer contains "5,180.2" or "5180.2" (±0.01)')
    assert score_task_success(row, answer="סה\"כ 5,180.20 ש\"ח", tool_calls=2, terminal_state="answered")[0] == "good"


def test_refusal_correctness_four_outcomes():
    assert refusal_correctness(answerable=False, terminal_state="refused") == "correct_refusal"
    assert refusal_correctness(answerable=False, terminal_state="answered") == "false_answer"
    assert refusal_correctness(answerable=True, terminal_state="answered") == "correct_answer"
    assert refusal_correctness(answerable=True, terminal_state="refused") == "false_refusal"
