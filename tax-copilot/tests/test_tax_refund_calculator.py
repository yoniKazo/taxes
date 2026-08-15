import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest

from tax_refund_calculator import InvalidInputError, calculate

# מקור: specs/tax-refund-calculator.md — טבלת Test vectors, baseline בלבד
# (extra_credit_points=0, ללא ניכויים/תרומה).
TEST_VECTORS = [
    (5000, "male", 500.00, 0.00, 52.00, 161.50, 4786.50),
    (13000, "male", 1716.00, 1171.50, 450.90, 522.66, 10854.94),
    (20000, "female", 3226.00, 2560.50, 940.90, 884.56, 15614.04),
    (45000, "male", 11772.00, 11227.50, 2690.90, 2177.06, 28904.54),
]


@pytest.mark.parametrize(
    "gross_salary, gender, tax_before_credit, tax_after_credit, ni, health, net",
    TEST_VECTORS,
)
def test_calculate_baseline_vectors(
    gross_salary, gender, tax_before_credit, tax_after_credit, ni, health, net
):
    result = calculate(gross_salary, gender)

    assert result.tax_before_credit == tax_before_credit
    assert result.tax_after_credit == tax_after_credit
    assert result.national_insurance == ni
    assert result.health_tax == health
    assert result.net == net


def test_calculate_negative_gross_salary_raises():
    with pytest.raises(InvalidInputError):
        calculate(-1000, "male")


def test_calculate_zero_gross_salary_raises():
    with pytest.raises(InvalidInputError):
        calculate(0, "male")


def test_calculate_invalid_gender_raises():
    with pytest.raises(InvalidInputError):
        calculate(5000, "other")
