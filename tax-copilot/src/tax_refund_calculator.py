"""מחשבון מס והחזר לשכיר — ראו specs/tax-refund-calculator.md. דטרמיניסטי, ללא LLM."""

import argparse
import sys
from dataclasses import dataclass

sys.stdout.reconfigure(encoding="utf-8")

# כל הקבועים לפי data/tax_notes.md, שנת מס 2026 בלבד (ראו Open Questions ב-CLAUDE.md).

# מקור: tax_notes.md §1 — (lower, upper, rate, cumulative_tax_at_lower)
TAX_BRACKETS = [
    (0, 7010, 0.10, 0.0),
    (7010, 10060, 0.14, 701.00),
    (10060, 19000, 0.20, 1128.00),
    (19000, 25100, 0.31, 2916.00),
    (25100, 46690, 0.35, 4807.00),
    (46690, float("inf"), 0.47, 12363.50),
]

# מקור: tax_notes.md §2
CREDIT_POINT_VALUE_MONTHLY = 242.0
BASE_CREDIT_POINTS = {"male": 2.25, "female": 2.75}

# מקור: tax_notes.md §3
NI_REDUCED_THRESHOLD = 7703.0
NI_CEILING = 51910.0
NI_RATE_LOW, NI_RATE_HIGH = 0.0104, 0.07
HEALTH_RATE_LOW, HEALTH_RATE_HIGH = 0.0323, 0.0517

# מקור: tax_notes.md §5 — תקרת הפקדה פטורה לקרן השתלמות
KEREN_HISHTALMUT_DEDUCTIBLE_CAP_MONTHLY = 1571.0

# מקור: tax_notes.md §7 — סעיף 46. אין תקרת % הכנסה חייבת מוקשחת כאן (תלוית-הכנסה, לא ניתנה כמספר קבוע במקור).
DONATION_CREDIT_RATE = 0.35
DONATION_MIN_ANNUAL = 207.0

CURRENT_TAX_YEAR = 2026

# מקור: tax_notes.md §2 — טבלת נקודות זיכוי לפי גיל ילד/הורה (kolzchut.org.il).
# (mother_points, father_points) לכל שנת גיל/טווח.
CHILD_CREDIT_POINTS_BY_AGE = {
    0: (2.5, 2.5),
    1: (4.5, 4.5),
    2: (4.5, 4.5),
    3: (3.5, 3.5),
    4: (2.5, 2.5),
    5: (2.5, 2.5),
    **{age: (2.0, 1.0) for age in range(6, 18)},  # 6-12 ו-13-17 שוות ערך בטבלת המקור
    18: (0.5, 0.5),
}

# מקור: tax_notes.md §2 — חייל/ת משוחרר/ת ומסיימי שירות לאומי-אזרחי (kolzchut.org.il).
# תקף ל-36 חודשים מתום השירות; (min_service_months -> נקודות/חודש).
DISCHARGED_SOLDIER_DURATION_MONTHS = 36
DISCHARGED_SOLDIER_THRESHOLDS = {
    ("military", "male"): [(23, 2.0), (12, 1.0)],
    ("military", "female"): [(22, 2.0), (12, 1.0)],
    ("national", "male"): [(24, 2.0), (12, 1.0)],
    ("national", "female"): [(24, 2.0), (12, 1.0)],
}

# מקור: tax_notes.md §2 — עולה חדש/קטין חוזר (bshcpa.co.il; ראו הסתייגות מקור בקובץ).
# תקף ל-54 חודשים מהעלייה; (max_months_in_window, points_in_window, window_length_months).
NEW_IMMIGRANT_WINDOWS = [
    (12, 1.0, 12),
    (30, 3.0, 18),
    (42, 2.0, 12),
    (54, 1.0, 12),
]

# מקור: tax_notes.md §2 — תואר אקדמי/תעודת הנדסאי (kolzchut.org.il).
ACADEMIC_DEGREE_NEW_RULE_FROM_YEAR = 2023
ACADEMIC_DEGREE_NEW_RULE_MAX_YEARS = 3
ACADEMIC_DEGREE_OLD_RULE_MIN_YEAR = 2014
ACADEMIC_DEGREE_OLD_RULE_MAX_YEAR = 2022
ACADEMIC_DEGREE_OLD_RULE_WINDOW = (1, 2)


class InvalidInputError(ValueError):
    pass


def estimate_child_credit_points(age: int, gender: str) -> float:
    if age not in CHILD_CREDIT_POINTS_BY_AGE:
        return 0.0
    mother_points, father_points = CHILD_CREDIT_POINTS_BY_AGE[age]
    return mother_points if gender == "female" else father_points


def estimate_discharged_soldier_points(
    gender: str,
    service_type: str,
    months_since_discharge: int,
    service_length_months: int,
) -> float:
    if not (1 <= months_since_discharge <= DISCHARGED_SOLDIER_DURATION_MONTHS):
        return 0.0
    thresholds = DISCHARGED_SOLDIER_THRESHOLDS.get((service_type, gender), [])
    for min_service_months, points in thresholds:
        if service_length_months >= min_service_months:
            return points
    return 0.0


def estimate_new_immigrant_points(months_since_aliyah: int) -> float:
    if months_since_aliyah <= 0:
        return 0.0
    for max_months, points, window_length in NEW_IMMIGRANT_WINDOWS:
        if months_since_aliyah <= max_months:
            return points / window_length
    return 0.0


def estimate_academic_degree_points(
    graduation_year: int, program_years: int, current_year: int = CURRENT_TAX_YEAR
) -> float:
    if program_years <= 0:
        return 0.0
    years_since_graduation = current_year - graduation_year

    if graduation_year >= ACADEMIC_DEGREE_NEW_RULE_FROM_YEAR:
        window = min(program_years, ACADEMIC_DEGREE_NEW_RULE_MAX_YEARS)
        return 1.0 if 1 <= years_since_graduation <= window else 0.0

    if ACADEMIC_DEGREE_OLD_RULE_MIN_YEAR <= graduation_year <= ACADEMIC_DEGREE_OLD_RULE_MAX_YEAR:
        low, high = ACADEMIC_DEGREE_OLD_RULE_WINDOW
        return 1.0 if low <= years_since_graduation <= high else 0.0

    return 0.0


@dataclass(frozen=True)
class TaxResult:
    tax_before_credit: float
    tax_after_credit: float
    national_insurance: float
    health_tax: float
    net: float
    pension_tax_savings: float
    keren_hishtalmut_tax_savings: float
    donation_credit_annual: float


def _validate(gross_salary: float, gender: str) -> None:
    if not isinstance(gross_salary, (int, float)) or gross_salary <= 0:
        raise InvalidInputError("שכר ברוטו חייב להיות מספר חיובי.")
    if gender not in BASE_CREDIT_POINTS:
        raise InvalidInputError('gender חייב להיות "male" או "female".')


def calc_income_tax(taxable: float) -> float:
    if taxable <= 0:
        return 0.0
    for lower, upper, rate, cum_at_lower in TAX_BRACKETS:
        if taxable <= upper:
            return cum_at_lower + (taxable - lower) * rate
    return 0.0


def calc_ni_and_health(gross_salary: float) -> tuple[float, float]:
    capped_gross = min(gross_salary, NI_CEILING)
    low_base = min(capped_gross, NI_REDUCED_THRESHOLD)
    high_base = max(capped_gross - NI_REDUCED_THRESHOLD, 0.0)
    ni = low_base * NI_RATE_LOW + high_base * NI_RATE_HIGH
    health = low_base * HEALTH_RATE_LOW + high_base * HEALTH_RATE_HIGH
    return round(ni, 2), round(health, 2)


def _final_tax_after_credit(taxable: float, credit_value: float) -> float:
    return max(calc_income_tax(taxable) - credit_value, 0.0)


def calculate(
    gross_salary: float,
    gender: str,
    extra_credit_points: float = 0.0,
    pension_employee_pct: float = 0.0,
    keren_hishtalmut_monthly: float = 0.0,
    annual_donation: float = 0.0,
) -> TaxResult:
    _validate(gross_salary, gender)

    credit_value = (BASE_CREDIT_POINTS[gender] + extra_credit_points) * CREDIT_POINT_VALUE_MONTHLY

    pension_deduction = gross_salary * pension_employee_pct
    keren_deduction = min(keren_hishtalmut_monthly, KEREN_HISHTALMUT_DEDUCTIBLE_CAP_MONTHLY)

    tax_after_credit_baseline = _final_tax_after_credit(gross_salary, credit_value)
    pension_tax_savings = tax_after_credit_baseline - _final_tax_after_credit(
        gross_salary - pension_deduction, credit_value
    )
    keren_tax_savings = tax_after_credit_baseline - _final_tax_after_credit(
        gross_salary - keren_deduction, credit_value
    )

    taxable = gross_salary - pension_deduction - keren_deduction
    tax_before_credit = round(calc_income_tax(taxable), 2)
    tax_after_credit = round(_final_tax_after_credit(taxable, credit_value), 2)

    ni, health = calc_ni_and_health(gross_salary)
    net = round(gross_salary - tax_after_credit - ni - health, 2)

    donation_credit_annual = (
        round(annual_donation * DONATION_CREDIT_RATE, 2)
        if annual_donation > DONATION_MIN_ANNUAL
        else 0.0
    )

    return TaxResult(
        tax_before_credit=tax_before_credit,
        tax_after_credit=tax_after_credit,
        national_insurance=ni,
        health_tax=health,
        net=net,
        pension_tax_savings=round(pension_tax_savings, 2),
        keren_hishtalmut_tax_savings=round(keren_tax_savings, 2),
        donation_credit_annual=donation_credit_annual,
    )


@dataclass(frozen=True)
class JobInput:
    gross_salary: float
    label: str = ""


@dataclass(frozen=True)
class MultiJobTaxResult:
    combined_gross: float
    job_count: int
    jobs: tuple[JobInput, ...]
    result: TaxResult


def _validate_jobs(jobs: list[JobInput]) -> None:
    if not jobs:
        raise InvalidInputError("יש לספק לפחות עבודה אחת.")
    for job in jobs:
        if not isinstance(job.gross_salary, (int, float)) or job.gross_salary <= 0:
            raise InvalidInputError("שכר ברוטו חייב להיות מספר חיובי.")


def calculate_multi_job(
    jobs: list[JobInput],
    gender: str,
    extra_credit_points: float = 0.0,
    pension_employee_pct: float = 0.0,
    keren_hishtalmut_monthly: float = 0.0,
    annual_donation: float = 0.0,
) -> MultiJobTaxResult:
    _validate_jobs(jobs)

    combined_gross = sum(job.gross_salary for job in jobs)
    result = calculate(
        combined_gross,
        gender,
        extra_credit_points=extra_credit_points,
        pension_employee_pct=pension_employee_pct,
        keren_hishtalmut_monthly=keren_hishtalmut_monthly,
        annual_donation=annual_donation,
    )

    return MultiJobTaxResult(
        combined_gross=combined_gross,
        job_count=len(jobs),
        jobs=tuple(jobs),
        result=result,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="מחשבון מס והחזר לשכיר (2026, שכירים בלבד)")
    parser.add_argument("gross_salary", type=float)
    parser.add_argument("gender", choices=["male", "female"])
    parser.add_argument("--extra-credit-points", type=float, default=0.0)
    parser.add_argument("--pension-pct", type=float, default=0.0)
    parser.add_argument("--keren-hishtalmut", type=float, default=0.0)
    parser.add_argument("--donation", type=float, default=0.0)
    args = parser.parse_args()

    try:
        result = calculate(
            gross_salary=args.gross_salary,
            gender=args.gender,
            extra_credit_points=args.extra_credit_points,
            pension_employee_pct=args.pension_pct,
            keren_hishtalmut_monthly=args.keren_hishtalmut,
            annual_donation=args.donation,
        )
    except InvalidInputError as e:
        print(f"שגיאה: {e}")
        return

    print(f"מס הכנסה לפני זיכוי: {result.tax_before_credit:.2f} ₪")
    print(f"מס הכנסה אחרי זיכוי: {result.tax_after_credit:.2f} ₪")
    print(f"ביטוח לאומי: {result.national_insurance:.2f} ₪")
    print(f"מס בריאות: {result.health_tax:.2f} ₪")
    print(f"נטו משוער: {result.net:.2f} ₪")
    if args.pension_pct > 0:
        print(f"חיסכון מס מהפרשת פנסיה: {result.pension_tax_savings:.2f} ₪")
    if args.keren_hishtalmut > 0:
        print(f"חיסכון מס מקרן השתלמות: {result.keren_hishtalmut_tax_savings:.2f} ₪")
    if args.donation > 0:
        print(f"זיכוי מס שנתי מתרומה (סעיף 46): {result.donation_credit_annual:.2f} ₪")


if __name__ == "__main__":
    main()
