"""מטלה 4, Task 2 -- בדיקות לחוזה הכישלון של שלושת ה-tools: לעולם לא raise,
לעולם לא None/"", תמיד מחרוזת "ERROR: ..."/"NO_RESULTS: ..." מסבירה בכשל.

src/tools.py מייבא מודולים אחיים ב-src/ (build_index, rag_pipeline,
tax_refund_calculator) בייבוא "עירום" -- אותו דפוס בדיוק כמו שאר src/*.py.
לכן, כמו tests/test_rag_backend.py/test_calculate_route.py, צריך גם את src/
עצמה על sys.path, לא רק את שורש הריפו.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

import pytest  # noqa: E402
from langchain_core.documents import Document  # noqa: E402

from src.tools import calculate_tax_refund, calculator, search_tax_corpus  # noqa: E402
from src.tools import _search_tax_corpus_impl  # noqa: E402


# --- calculator --------------------------------------------------------------


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("2 + 2", "4"),
        ("0.18 * 4390", "790.2"),
        ("(10 + 5) * 2", "30"),
        ("2 ** 10", "1024"),
        ("-5 + 3", "-2"),
        ("100 / 4", "25"),
    ],
)
def test_calculator_evaluates_arithmetic(expression, expected):
    assert calculator.invoke({"expression": expression}) == expected


def test_calculator_division_by_zero_returns_error_string():
    result = calculator.invoke({"expression": "1 / 0"})
    assert result.startswith("ERROR:")


def test_calculator_malformed_expression_returns_error_string():
    result = calculator.invoke({"expression": "2 + "})
    assert result.startswith("ERROR:")


def test_calculator_rejects_non_arithmetic_input_safely():
    """הקלט מגיע מ-LLM; אסור שיהיה נתיב להרצת קוד שרירותי."""
    for malicious in ["__import__('os').system('echo pwned')", "open('x').read()", "[].__class__"]:
        result = calculator.invoke({"expression": malicious})
        assert result.startswith("ERROR:"), f"expected ERROR for {malicious!r}, got {result!r}"


def test_calculator_never_raises():
    for bad in ["", "   ", "2 +++ 2", "'a' + 'b'", "2; 3"]:
        result = calculator.invoke({"expression": bad})
        assert isinstance(result, str) and result


# --- calculate_tax_refund ------------------------------------------------------


def test_calculate_tax_refund_matches_underlying_calculator():
    from src.tax_refund_calculator import calculate

    expected = calculate(15000.0, "male")
    result = calculate_tax_refund.invoke({"gross_salary": 15000.0, "gender": "male"})
    assert f"{expected.net:.2f}" in result
    assert f"{expected.tax_after_credit:.2f}" in result


def test_calculate_tax_refund_invalid_gender_returns_error_string():
    result = calculate_tax_refund.invoke({"gross_salary": 15000.0, "gender": "other"})
    assert result.startswith("ERROR:")


def test_calculate_tax_refund_non_positive_salary_returns_error_string():
    result = calculate_tax_refund.invoke({"gross_salary": 0.0, "gender": "male"})
    assert result.startswith("ERROR:")


def test_calculate_tax_refund_never_raises():
    for salary, gender in [(-100.0, "male"), (0.0, "female"), (15000.0, "unspecified")]:
        result = calculate_tax_refund.invoke({"gross_salary": salary, "gender": gender})
        assert isinstance(result, str) and result


# --- search_tax_corpus ---------------------------------------------------------


class _FakeVectorstore:
    def __init__(self, chunks):
        self._chunks = chunks

    def similarity_search(self, query, k=5):
        return self._chunks[:k]


def _doc(text, doc_name="employees-tax-guide", section="1. מבוא"):
    return Document(page_content=text, metadata={"doc_name": doc_name, "section": section, "page": None})


def test_search_tax_corpus_impl_formats_hits_with_doc_and_section():
    vectorstore = _FakeVectorstore([_doc("מדרגת המס הראשונה היא 10%.")])
    result = _search_tax_corpus_impl("מהי מדרגת המס הראשונה?", 5, vectorstore)
    assert "employees-tax-guide" in result
    assert "10%" in result


def test_search_tax_corpus_impl_no_results_returns_explanatory_string():
    vectorstore = _FakeVectorstore([])
    result = _search_tax_corpus_impl("שאלה שלא קיימת בקורפוס", 5, vectorstore)
    assert result.startswith("NO_RESULTS:")


def test_search_tax_corpus_is_a_tool_with_query_and_k_args():
    assert set(search_tax_corpus.args) >= {"query"}
