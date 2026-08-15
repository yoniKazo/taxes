"""POST /calculate, GET /health."""

import sqlite3

from fastapi import APIRouter, Depends

from api.agents import explainer
from api.agents.base import AgentCallError
from api.routes._common import get_agent, get_db, log_llm_call, resolve_overrides
from api.schemas import CalculateRequest, CalculateResponse
from src.tax_refund_calculator import JobInput, calculate_multi_job

router = APIRouter()

_GENDER_HE = {"male": "זכר", "female": "נקבה"}


def _build_context(payload: CalculateRequest, multi) -> str:
    result = multi.result
    lines = [
        f"מספר עבודות: {multi.job_count}",
        f"סך שכר ברוטו משולב: {multi.combined_gross:.2f} ₪",
        f"מגדר: {_GENDER_HE.get(payload.gender, payload.gender)}",
        f"נקודות זיכוי נוספות: {payload.extra_credit_points}",
        f"מס הכנסה לפני זיכוי: {result.tax_before_credit:.2f} ₪",
        f"מס הכנסה אחרי זיכוי: {result.tax_after_credit:.2f} ₪",
        f"ביטוח לאומי: {result.national_insurance:.2f} ₪",
        f"מס בריאות: {result.health_tax:.2f} ₪",
        f"נטו משוער: {result.net:.2f} ₪",
        f"חיסכון מס מהפרשת פנסיה: {result.pension_tax_savings:.2f} ₪",
        f"חיסכון מס מקרן השתלמות: {result.keren_hishtalmut_tax_savings:.2f} ₪",
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
    jobs = [JobInput(gross_salary=j.gross_salary, label=j.label) for j in payload.jobs]
    multi = calculate_multi_job(
        jobs,
        payload.gender,
        extra_credit_points=payload.extra_credit_points,
        pension_employee_pct=payload.pension_employee_pct,
        keren_hishtalmut_monthly=payload.keren_hishtalmut_monthly,
        annual_donation=payload.annual_donation,
    )
    result = multi.result

    explanation: str | None = None
    explanation_error: str | None = None

    if payload.include_explanation:
        context = _build_context(payload, multi)
        agent_row = get_agent(conn, "explainer")
        # explainer agent is seeded at startup -- if it's genuinely missing this
        # is a setup bug, not a user input error, so degrade gracefully same as
        # an LLM failure rather than 500ing the whole calculation response.
        if agent_row is None:
            explanation_error = "סוכן ההסבר אינו מוגדר במערכת."
        else:
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

    return CalculateResponse(
        combined_gross=multi.combined_gross,
        job_count=multi.job_count,
        tax_before_credit=result.tax_before_credit,
        tax_after_credit=result.tax_after_credit,
        national_insurance=result.national_insurance,
        health_tax=result.health_tax,
        net=result.net,
        pension_tax_savings=result.pension_tax_savings,
        keren_hishtalmut_tax_savings=result.keren_hishtalmut_tax_savings,
        donation_credit_annual=result.donation_credit_annual,
        explanation=explanation,
        explanation_error=explanation_error,
    )
