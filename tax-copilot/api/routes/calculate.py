"""POST /calculate, GET /health."""

import sqlite3

from fastapi import APIRouter, Depends

from api.agents import explainer
from api.agents.base import AgentCallError
from api.routes._common import get_agent, get_db, log_llm_call, resolve_overrides
from api.schemas import CalculateRequest, CalculateResponse
from src.tax_refund_calculator import (
    BASE_CREDIT_POINTS,
    JobInput,
    calculate_multi_job,
    estimate_academic_degree_points,
    estimate_child_credit_points,
    estimate_discharged_soldier_points,
    estimate_new_immigrant_points,
)

router = APIRouter()

_GENDER_HE = {"male": "זכר", "female": "נקבה"}


def _estimate_credit_points(payload: CalculateRequest) -> float:
    total = 0.0
    for child in payload.children:
        total += estimate_child_credit_points(child.age, payload.gender)
    if payload.is_single_parent:
        total += 1.0
    if payload.lives_in_eligible_zone:
        total += 1.0
    if payload.discharged_service is not None:
        ds = payload.discharged_service
        total += estimate_discharged_soldier_points(
            payload.gender, ds.service_type, ds.months_since_discharge, ds.service_length_months
        )
    if payload.new_immigrant is not None:
        total += estimate_new_immigrant_points(payload.new_immigrant.months_since_aliyah)
    if payload.academic_degree is not None:
        ad = payload.academic_degree
        total += estimate_academic_degree_points(ad.graduation_year, ad.program_years)
    return total


def _build_context(payload: CalculateRequest, multi, estimated_credit_points: float) -> str:
    result = multi.result
    lines = [
        f"מספר עבודות: {multi.job_count}",
        f"סך שכר ברוטו משולב (שנתי): {multi.combined_gross * 12:.2f} ₪",
        f"מגדר: {_GENDER_HE.get(payload.gender, payload.gender)}",
        f"נקודות זיכוי בסיס: {BASE_CREDIT_POINTS[payload.gender]}",
        f"נקודות זיכוי מוערכות מעובדות (ילדים/הורה יחיד/אזור זכאי/שירות/עלייה/תואר): "
        f"{estimated_credit_points:.2f}",
        f"נקודות זיכוי נוספות ידניות: {payload.extra_credit_points}",
        f"מס הכנסה לפני זיכוי (שנתי): {result.tax_before_credit * 12:.2f} ₪",
        f"מס הכנסה אחרי זיכוי (שנתי): {result.tax_after_credit * 12:.2f} ₪",
        f"ביטוח לאומי (שנתי): {result.national_insurance * 12:.2f} ₪",
        f"מס בריאות (שנתי): {result.health_tax * 12:.2f} ₪",
        f"נטו משוער (שנתי): {result.net * 12:.2f} ₪",
        f"חיסכון מס מהפרשת פנסיה (שנתי): {result.pension_tax_savings * 12:.2f} ₪",
        f"חיסכון מס מקרן השתלמות (שנתי): {result.keren_hishtalmut_tax_savings * 12:.2f} ₪",
        f"זיכוי מס שנתי מתרומה (סעיף 46): {result.donation_credit_annual:.2f} ₪",
    ]
    return "\n".join(lines)


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/calculate", response_model=CalculateResponse)
def calculate_endpoint(
    payload: CalculateRequest, conn: sqlite3.Connection = Depends(get_db)
) -> CalculateResponse:
    # payload מגיע שנתי מהלקוח; המנוע (tax_refund_calculator) עובד חודשית פנימית.
    jobs = [JobInput(gross_salary=j.gross_salary / 12, label=j.label) for j in payload.jobs]
    estimated_credit_points = _estimate_credit_points(payload)
    total_extra_credit_points = estimated_credit_points + payload.extra_credit_points

    multi = calculate_multi_job(
        jobs,
        payload.gender,
        extra_credit_points=total_extra_credit_points,
        pension_employee_pct=payload.pension_employee_pct,
        keren_hishtalmut_monthly=payload.keren_hishtalmut_annual / 12,
        annual_donation=payload.annual_donation,
    )
    result = multi.result

    explanation: str | None = None
    explanation_error: str | None = None

    if payload.include_explanation:
        context = _build_context(payload, multi, estimated_credit_points)
        agent_row = get_agent(conn, "explainer")
        model, system_prompt, temperature = resolve_overrides(agent_row, None, None, None)
        try:
            explain_result = explainer.explain(
                context, model=model, system_prompt=system_prompt, temperature=temperature
            )
            explanation = explain_result.text
            log_llm_call(
                conn,
                agent_name="explainer",
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
                question=context,
                response=explanation,
                latency_ms=explain_result.latency_ms,
                input_tokens=explain_result.input_tokens,
                output_tokens=explain_result.output_tokens,
                source="live",
            )
        except AgentCallError as e:
            explanation_error = "לא ניתן היה להפיק הסבר כרגע. תוצאות החישוב עדיין תקפות."
            log_llm_call(
                conn,
                agent_name="explainer",
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
                question=context,
                response=None,
                latency_ms=None,
                input_tokens=None,
                output_tokens=None,
                source="live",
                error=str(e),
            )

    total_credit_points = BASE_CREDIT_POINTS[payload.gender] + total_extra_credit_points

    return CalculateResponse(
        combined_gross=multi.combined_gross,
        job_count=multi.job_count,
        estimated_credit_points=round(estimated_credit_points, 2),
        total_credit_points=round(total_credit_points, 2),
        tax_before_credit=result.tax_before_credit,
        tax_after_credit=result.tax_after_credit,
        national_insurance=result.national_insurance,
        health_tax=result.health_tax,
        net=result.net,
        pension_tax_savings=result.pension_tax_savings,
        keren_hishtalmut_tax_savings=result.keren_hishtalmut_tax_savings,
        combined_gross_annual=round(multi.combined_gross * 12, 2),
        tax_before_credit_annual=round(result.tax_before_credit * 12, 2),
        tax_after_credit_annual=round(result.tax_after_credit * 12, 2),
        national_insurance_annual=round(result.national_insurance * 12, 2),
        health_tax_annual=round(result.health_tax * 12, 2),
        net_annual=round(result.net * 12, 2),
        pension_tax_savings_annual=round(result.pension_tax_savings * 12, 2),
        keren_hishtalmut_tax_savings_annual=round(result.keren_hishtalmut_tax_savings * 12, 2),
        donation_credit_annual=result.donation_credit_annual,
        explanation=explanation,
        explanation_error=explanation_error,
    )
