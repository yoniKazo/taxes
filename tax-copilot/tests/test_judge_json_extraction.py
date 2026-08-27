"""מטלה 4 -- בדיקות ל-_strip_fence: חילוץ JSON מתשובת judge שעלולה להגיע עטופה
ב-code fence, או (נצפה בפועל מול claude-sonnet-5 עם tool_outputs ארוכים) עם פרוזה
לפני/מסביב ל-JSON למרות ההוראה "אך ורק JSON"."""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from src.assignment4_judges import _strip_fence as strip_fence_judges  # noqa: E402
from src.evaluator_optimizer import _strip_fence as strip_fence_optimizer  # noqa: E402

PLAIN_JSON = '{"explanation": "ok", "verdict": "good"}'


def test_strip_fence_handles_plain_json():
    assert strip_fence_judges(PLAIN_JSON) == PLAIN_JSON
    assert strip_fence_optimizer(PLAIN_JSON) == PLAIN_JSON


def test_strip_fence_handles_json_fence_with_language_tag():
    raw = f"```json\n{PLAIN_JSON}\n```"
    assert strip_fence_judges(raw) == PLAIN_JSON


def test_strip_fence_handles_bare_fence():
    raw = f"```\n{PLAIN_JSON}\n```"
    assert strip_fence_judges(raw) == PLAIN_JSON


def test_strip_fence_extracts_json_from_surrounding_prose():
    """המקרה שנתפס בפועל מול Task 5: המודל פותח בפרוזה עברית לפני ה-JSON, למרות
    הוראת "אך ורק JSON" -- קורה במיוחד כש-tool_outputs ארוך."""
    raw = 'לפי סעיף 3.2, ענית נכון. {"explanation": "תשובה מבוססת", "verdict": "good"} תודה.'
    result = strip_fence_judges(raw)
    parsed = json.loads(result)
    assert parsed["verdict"] == "good"
    assert parsed["explanation"] == "תשובה מבוססת"


def test_strip_fence_both_modules_agree():
    raw = 'הסבר לפני. {"explanation": "x", "verdict": "ok"}'
    assert strip_fence_judges(raw) == strip_fence_optimizer(raw)
