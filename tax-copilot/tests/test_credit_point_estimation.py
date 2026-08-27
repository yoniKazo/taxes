"""בדיקות לפונקציות הערכת נקודות זיכוי מבוססות-עובדות (ילדים, חייל/ת משוחרר/ת,
עולה חדש/קטין חוזר, תואר אקדמי) — ראו plan + data/tax_notes.md §2 למקורות."""

import pytest

from src.tax_refund_calculator import (
    estimate_academic_degree_points,
    estimate_child_credit_points,
    estimate_discharged_soldier_points,
    estimate_new_immigrant_points,
)


@pytest.mark.parametrize(
    "age, gender, expected",
    [
        (0, "female", 2.5),
        (0, "male", 2.5),
        (1, "female", 4.5),
        (2, "male", 4.5),
        (3, "female", 3.5),
        (4, "male", 2.5),
        (5, "female", 2.5),
        (6, "female", 2.0),
        (6, "male", 1.0),
        (12, "female", 2.0),
        (13, "male", 1.0),
        (17, "female", 2.0),
        (18, "male", 0.5),
        (18, "female", 0.5),
        (19, "male", 0.0),
        (-1, "female", 0.0),
    ],
)
def test_estimate_child_credit_points(age, gender, expected):
    assert estimate_child_credit_points(age, gender) == expected


@pytest.mark.parametrize(
    "gender, service_type, months_since_discharge, service_length_months, expected",
    [
        ("male", "military", 1, 23, 2.0),
        ("male", "military", 36, 23, 2.0),
        ("male", "military", 37, 23, 0.0),
        ("male", "military", 12, 22, 1.0),
        ("male", "military", 12, 11, 0.0),
        ("female", "military", 12, 22, 2.0),
        ("female", "military", 12, 21, 1.0),
        ("female", "military", 12, 11, 0.0),
        ("male", "national", 12, 24, 2.0),
        ("male", "national", 12, 12, 1.0),
        ("male", "national", 12, 11, 0.0),
        ("male", "military", 0, 23, 0.0),
    ],
)
def test_estimate_discharged_soldier_points(
    gender, service_type, months_since_discharge, service_length_months, expected
):
    assert (
        estimate_discharged_soldier_points(
            gender, service_type, months_since_discharge, service_length_months
        )
        == expected
    )


@pytest.mark.parametrize(
    "months_since_aliyah, expected",
    [
        (0, 0.0),
        (1, 1 / 12),
        (12, 1 / 12),
        (13, 3 / 18),
        (30, 3 / 18),
        (31, 2 / 12),
        (42, 2 / 12),
        (43, 1 / 12),
        (54, 1 / 12),
        (55, 0.0),
    ],
)
def test_estimate_new_immigrant_points(months_since_aliyah, expected):
    assert estimate_new_immigrant_points(months_since_aliyah) == pytest.approx(expected)


@pytest.mark.parametrize(
    "graduation_year, program_years, current_year, expected",
    [
        # סיום 2023+: נקודה אחת לשנה, min(program_years, 3) שנים, החל משנה אחרי הסיום.
        (2026, 3, 2026, 0.0),  # עדיין באותה שנת הסיום -- לא התחיל
        (2025, 3, 2026, 1.0),  # שנה 1 אחרי הסיום
        (2024, 3, 2026, 1.0),  # שנה 2 אחרי הסיום, עדיין בתוך תואר 3 שנים
        (2023, 2, 2026, 0.0),  # שנה 3 אחרי הסיום, אבל תואר של שנתיים בלבד -- נגמר
        (2023, 3, 2026, 1.0),  # שנה 3 אחרי הסיום, תואר 3 שנים -- עדיין בתוך החלון
        (2020, 4, 2026, 0.0),  # שנה 6 אחרי הסיום -- מעבר לתקרת 3 השנים
        (2027, 3, 2026, 0.0),  # סיום עתידי
        # סיום 2014-2022: נקודה אחת לשנה בודדת, בשנה שאחרי הסיום או בדחייה של שנה.
        (2020, 4, 2021, 1.0),
        (2020, 4, 2022, 1.0),
        (2020, 4, 2023, 0.0),
        (2005, 4, 2026, 0.0),  # לפני 2014 -- לא מכוסה
    ],
)
def test_estimate_academic_degree_points(graduation_year, program_years, current_year, expected):
    assert (
        estimate_academic_degree_points(graduation_year, program_years, current_year=current_year)
        == expected
    )
