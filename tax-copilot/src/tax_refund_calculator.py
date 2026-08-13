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


class InvalidInputError(ValueError):
    pass


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
