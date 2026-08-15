"""Pydantic request/response models for the FastAPI layer (api/main.py + api/routes/*).

Calculator shapes are exactly per plan section 5's code block. Test Lab shapes
follow the JSON contract documented by the (already-built) React client in
web/src/api/client.js and the components under web/src/components/ -- see
plan section 5 for the full response-shape spec this file implements.
"""

from typing import Literal

from pydantic import BaseModel

# --- מחשבון ---


class JobIn(BaseModel):
    gross_salary: float
    label: str = ""


class CalculateRequest(BaseModel):
    jobs: list[JobIn]
    gender: Literal["male", "female"]
    extra_credit_points: float = 0.0
    pension_employee_pct: float = 0.0
    keren_hishtalmut_monthly: float = 0.0
    annual_donation: float = 0.0
    include_explanation: bool = True


class CalculateResponse(BaseModel):
    combined_gross: float
    job_count: int
    tax_before_credit: float
    tax_after_credit: float
    national_insurance: float
    health_tax: float
    net: float
    pension_tax_savings: float
    keren_hishtalmut_tax_savings: float
    donation_credit_annual: float
    explanation: str | None
    explanation_error: str | None = None


# --- Agents ---


class AgentOut(BaseModel):
    name: str
    description: str | None
    default_model: str
    default_system_prompt: str
    default_temperature: float


# --- Rubrics ---
# go/no-go is a separate table (rubric_go_no_go) in the DB but is merged INTO
# each criterion object here, per the frontend's documented shape -- RubricPanel
# reads/writes fails_unless_good/fails_if_bad directly on each criterion row.


class RubricCriterionIO(BaseModel):
    name: str
    good_def: str
    ok_def: str
    bad_def: str
    is_programmatic: bool
    sort_order: int
    fails_unless_good: bool = False
    fails_if_bad: bool = False


class RubricIO(BaseModel):
    """Used both as the GET/PUT /rubrics/active response shape and as the PUT
    request body -- RubricPanel's draft state mirrors this shape exactly."""

    name: str
    pass_bar_min_good: int
    pass_bar_max_bad: int
    criteria: list[RubricCriterionIO]


# --- Test questions ---


class TestQuestionIn(BaseModel):
    dataset_name: str
    category: str | None = None
    question_text: str


class TestQuestionOut(BaseModel):
    id: int
    dataset_name: str
    category: str | None
    question_text: str
    is_active: bool


# --- Test runs ---


class TestRunRequest(BaseModel):
    agent_name: str
    model: str | None = None  # None => falls back to the agent's DB default
    temperature: float | None = None
    system_prompt: str | None = None
    question_ids: list[int]
    label: str = ""


class RatingRequest(BaseModel):
    rater: Literal["human"]  # judge is only ever written via /test-runs/{id}/judge
    scores: dict[str, Literal["good", "ok", "bad"]]


class TestRunListItem(BaseModel):
    id: int
    created_at: str
    agent_name: str
    model: str
    temperature: float
    label: str | None
    pass_percentage: float | None


class CriterionJudgeVerdict(BaseModel):
    verdict: str
    explanation: str


class TestRunResultItem(BaseModel):
    llm_call_id: int
    question_id: int | None
    question_text: str
    response: str | None
    latency_ms: float | None
    input_tokens: int | None
    output_tokens: int | None
    error: str | None
    human_ratings: dict[str, str]
    human_final_score: str | None
    judge_ratings: dict[str, CriterionJudgeVerdict]
    judge_final_score: str | None


class TestRunDetail(BaseModel):
    id: int
    created_at: str
    agent_name: str
    rubric_id: int
    model: str
    temperature: float
    system_prompt: str
    label: str | None
    results: list[TestRunResultItem]


# --- Agreement ---


class AgreementPerCriterion(BaseModel):
    criterion: str
    agreement_pct: float
    total: int


class Disagreement(BaseModel):
    llm_call_id: int
    question_text: str
    criterion: str
    human_verdict: str
    judge_verdict: str
    judge_explanation: str


class AgreementResponse(BaseModel):
    per_criterion: list[AgreementPerCriterion]
    disagreements: list[Disagreement]
