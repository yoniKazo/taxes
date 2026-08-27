"""בדיקות ל-POST /calculate: המרת שנתי->חודשי בגבול ה-API, וצירוף נקודות זיכוי
מוערכות מעובדות (ילדים/הורה יחיד/אזור זכאי) לתוך extra_credit_points.

include_explanation=False בכל הבדיקות -- כדי לא לגעת ב-DB/LLM, ראו
tests/test_rag_backend.py לאותו דפוס (TestClient, בלי הרשאה נחוצה).
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from src.tax_refund_calculator import calculate  # noqa: E402

client = TestClient(app)


def _payload(**overrides):
    base = {
        "jobs": [{"gross_salary": 156000.0, "label": ""}],  # 13,000/חודש * 12
        "gender": "male",
        "include_explanation": False,
    }
    base.update(overrides)
    return base


def test_annual_salary_is_divided_by_12_before_reaching_the_engine():
    response = client.post("/calculate", json=_payload())
    assert response.status_code == 200
    body = response.json()

    expected = calculate(13000.0, "male")
    assert body["tax_after_credit"] == expected.tax_after_credit
    assert body["net"] == expected.net
    assert body["net_annual"] == round(expected.net * 12, 2)
    assert body["combined_gross_annual"] == 156000.0


def test_keren_hishtalmut_annual_is_divided_by_12_before_reaching_the_engine():
    response = client.post("/calculate", json=_payload(keren_hishtalmut_annual=12000.0))
    assert response.status_code == 200
    body = response.json()

    expected = calculate(13000.0, "male", keren_hishtalmut_monthly=1000.0)
    assert body["keren_hishtalmut_tax_savings"] == expected.keren_hishtalmut_tax_savings


def test_credit_point_facts_are_estimated_and_summed_into_extra_credit_points():
    response = client.post(
        "/calculate",
        json=_payload(
            children=[{"age": 1}, {"age": 8}],
            is_single_parent=True,
            lives_in_eligible_zone=True,
        ),
    )
    assert response.status_code == 200
    body = response.json()

    # ילד בגיל 1 (4.5, אב) + ילד בגיל 8 (1.0, אב) + הורה יחיד (1.0) + אזור זכאי (1.0) = 7.5
    assert body["estimated_credit_points"] == 7.5
    assert body["total_credit_points"] == 2.25 + 7.5

    expected = calculate(13000.0, "male", extra_credit_points=7.5)
    assert body["tax_after_credit"] == expected.tax_after_credit


def test_manual_extra_credit_points_are_added_on_top_of_estimated():
    response = client.post(
        "/calculate", json=_payload(children=[{"age": 1}], extra_credit_points=2.0)
    )
    assert response.status_code == 200
    body = response.json()

    assert body["estimated_credit_points"] == 4.5
    assert body["total_credit_points"] == 2.25 + 4.5 + 2.0
