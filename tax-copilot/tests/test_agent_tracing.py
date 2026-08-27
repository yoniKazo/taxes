"""מטלה 4, Task 3.3 -- בדיקות ל-SafetyNets.breach(): כל חריגה מזוהה בנפרד,
ואף שילוב לא יחרוג בטעות כשכל שלוש המגבלות עדיין בתחום."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from src.agent_tracing import SafetyNets  # noqa: E402


def test_no_breach_within_all_limits():
    nets = SafetyNets(max_iterations=12, token_budget=30_000, timeout_s=90.0)
    assert nets.breach(steps=5, tokens_used=10_000, elapsed_s=10.0) is None


def test_max_iterations_breach():
    nets = SafetyNets(max_iterations=12, token_budget=30_000, timeout_s=90.0)
    assert nets.breach(steps=12, tokens_used=1_000, elapsed_s=1.0) == "max_iterations"


def test_token_budget_breach():
    nets = SafetyNets(max_iterations=12, token_budget=30_000, timeout_s=90.0)
    assert nets.breach(steps=1, tokens_used=30_000, elapsed_s=1.0) == "token_budget"


def test_timeout_breach():
    nets = SafetyNets(max_iterations=12, token_budget=30_000, timeout_s=90.0)
    assert nets.breach(steps=1, tokens_used=1, elapsed_s=90.0) == "timeout"


def test_breach_checked_in_order_max_iterations_first():
    """כששתי חריגות מתקיימות בו-זמנית, יש סדר עדיפות דטרמיניסטי, לא תלוי-מזל."""
    nets = SafetyNets(max_iterations=1, token_budget=1, timeout_s=1.0)
    assert nets.breach(steps=1, tokens_used=1, elapsed_s=1.0) == "max_iterations"
