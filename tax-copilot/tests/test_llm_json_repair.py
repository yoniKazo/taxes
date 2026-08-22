"""Unit tests for llm.repair_json_quotes -- the fix for Gemini emitting Hebrew
gershayim raw inside JSON strings (מע"מ, בע"מ, דו"ח).

Pure string logic, no network. The cases below are taken from the actual
malformed response that broke the Task 4 run, plus the boundary cases the
heuristic has to get right to be safe to apply as a fallback.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest

from llm import repair_json_quotes

# Verbatim from the row-19 failure: `sources` escaped correctly, `answer` did not.
REAL_FAILURE = (
    '{"answer": "עוסק שמחזורו מעל 1.5 מיליון ₪ חייב בדיווח מע"מ אחת לחודש [1].", '
    '"sources": ["general-tax-guide | סעיף: 1. מע\\"מ (מס ערך מוסף)"], '
    '"evidence": ["דיווח ותשלום מע"מ הוא תקופתי - אחת לחודש."], '
    '"answered": true}'
)


def test_repairs_the_real_gemini_failure():
    parsed = json.loads(repair_json_quotes(REAL_FAILURE))
    assert 'מע"מ' in parsed["answer"]
    assert parsed["answered"] is True
    assert parsed["sources"] == ['general-tax-guide | סעיף: 1. מע"מ (מס ערך מוסף)']


def test_leaves_valid_json_unchanged():
    """The repair runs as a fallback on every structured call, so it must never
    corrupt a response that was already well-formed."""
    valid = '{"answer": "25%", "sources": ["a", "b"], "evidence": [], "answered": true}'
    assert json.loads(repair_json_quotes(valid)) == json.loads(valid)


def test_preserves_already_escaped_quotes():
    raw = '{"answer": "בע\\"מ"}'
    assert json.loads(repair_json_quotes(raw))["answer"] == 'בע"מ'


@pytest.mark.parametrize("structural", [":", ",", "}", "]"])
def test_quote_before_structural_char_still_closes_the_string(structural):
    """A quote followed by : , } or ] is a real terminator, not a literal."""
    raw = {
        ":": '{"k": "v"}',
        ",": '{"a": "x", "b": "y"}',
        "}": '{"a": "x"}',
        "]": '{"a": ["x"]}',
    }[structural]
    assert json.loads(repair_json_quotes(raw)) == json.loads(raw)


def test_handles_quote_followed_by_whitespace_then_structural():
    raw = '{"answer": "מע"מ"   ,   "answered": false}'
    parsed = json.loads(repair_json_quotes(raw))
    assert parsed["answer"] == 'מע"מ'
    assert parsed["answered"] is False


def test_repairs_multiple_gershayim_in_one_value():
    raw = '{"answer": "חברה בע"מ חייבת בדיווח מע"מ ובהגשת דו"ח שנתי."}'
    assert repair_json_quotes(raw) and json.loads(repair_json_quotes(raw))["answer"].count('"') == 3


def test_does_not_escape_quotes_outside_strings():
    raw = '{"a": 1, "b": [2, 3]}'
    assert repair_json_quotes(raw) == raw
