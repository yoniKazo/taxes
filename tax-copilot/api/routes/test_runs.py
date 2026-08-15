"""POST /test-runs, GET /test-runs, GET /test-runs/{id},
POST /llm-calls/{id}/ratings, POST /test-runs/{id}/judge,
GET /test-runs/{id}/agreement.

Note on question_id linkage: llm_calls has no question_id FK column (see
schema.sql) -- only llm_calls.question (the verbatim question text sent).
This module always logs that field as the bare test_questions.question_text
(never the full document-wrapped prompt qa.answer() builds internally), so
GET /test-runs/{id} can recover question_id via a text match
(_common.find_question_by_text). See that helper's docstring.

Note on agent_name scope (plan section "Context"/decision #5): the Test Lab
v1 dataset (tax_qa_v1) is question-answering, so POST /test-runs always
generates answers via qa.answer() regardless of the requested agent_name --
if a caller asks for a different agent_name, the call shape/dataset are still
qa's; only agent_name/model/system_prompt/temperature bookkeeping reflects
the request. Judging that data against another agent later would need a
different dataset, which is out of scope here.
"""

import json
import sqlite3
import time

from fastapi import APIRouter, Depends, HTTPException

from api.agents import qa
from api.agents import judge as judge_agent_module
from api.agents.base import AgentCallError
from api.routes._common import (
    build_rubric_text,
    find_question_by_text,
    get_agent,
    get_db,
    get_rubric_criteria,
    go_no_go_list,
    load_tax_notes,
    log_llm_call,
    now_iso,
    resolve_overrides,
)
from api.schemas import (
    AgreementPerCriterion,
    AgreementResponse,
    CriterionJudgeVerdict,
    Disagreement,
    RatingRequest,
    TestRunDetail,
    TestRunListItem,
    TestRunRequest,
    TestRunResultItem,
)
from api.scoring import compute_agreement, compute_final_score, latency_rating

router = APIRouter()

# Gemini free tier throttling between sequential calls in a batch loop, per
# .claude/rules/hosted-llm-quota.md (same spirit as qa_experiment.py).
THROTTLE_SECONDS = 4

_JUDGE_CRITERION_MAP = {
    "fluency": "Fluency",
    "grammar": "Grammar",
    "tone": "Tone",
    "length": "Length",
    "grounding": "Grounding",
}


def _upsert_rating(
    conn: sqlite3.Connection,
    *,
    llm_call_id: int,
    rater: str,
    criterion: str | None,
    verdict: str | None,
    explanation: str | None,
) -> None:
    conn.execute(
        "DELETE FROM ratings WHERE llm_call_id = ? AND rater = ? AND criterion IS ?",
        (llm_call_id, rater, criterion),
    )
    conn.execute(
        "INSERT INTO ratings (llm_call_id, rater, criterion, verdict, explanation, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (llm_call_id, rater, criterion, verdict, explanation, now_iso()),
    )


def _get_test_run(conn: sqlite3.Connection, run_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM test_runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="ריצת בדיקה לא נמצאה.")
    return row


def _run_llm_calls(conn: sqlite3.Connection, run: sqlite3.Row) -> list[sqlite3.Row]:
    """The llm_calls rows that are actual tested results for this run --
    excludes the judge agent's own bookkeeping calls (agent_name='judge'),
    which are logged separately during POST /test-runs/{id}/judge."""
    return conn.execute(
        "SELECT * FROM llm_calls WHERE test_run_id = ? AND agent_name = ? ORDER BY id",
        (run["id"], run["agent_name"]),
    ).fetchall()


def _ratings_for_call(conn: sqlite3.Connection, llm_call_id: int, rater: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM ratings WHERE llm_call_id = ? AND rater = ?",
        (llm_call_id, rater),
    ).fetchall()


def _build_result_item(conn: sqlite3.Connection, call_row: sqlite3.Row) -> TestRunResultItem:
    question_row = find_question_by_text(conn, call_row["question"])

    human_rows = _ratings_for_call(conn, call_row["id"], "human")
    judge_rows = _ratings_for_call(conn, call_row["id"], "judge")

    human_ratings = {r["criterion"]: r["verdict"] for r in human_rows if r["criterion"] is not None}
    human_final_score = next((r["verdict"] for r in human_rows if r["criterion"] is None), None)

    judge_ratings = {
        r["criterion"]: CriterionJudgeVerdict(verdict=r["verdict"], explanation=r["explanation"] or "")
        for r in judge_rows
        if r["criterion"] is not None
    }
    judge_final_score = next((r["verdict"] for r in judge_rows if r["criterion"] is None), None)

    return TestRunResultItem(
        llm_call_id=call_row["id"],
        question_id=question_row["id"] if question_row else None,
        question_text=question_row["question_text"] if question_row else call_row["question"],
        response=call_row["response"],
        latency_ms=call_row["latency_ms"],
        input_tokens=call_row["input_tokens"],
        output_tokens=call_row["output_tokens"],
        error=call_row["error"],
        human_ratings=human_ratings,
        human_final_score=human_final_score,
        judge_ratings=judge_ratings,
        judge_final_score=judge_final_score,
    )


def _build_test_run_detail(conn: sqlite3.Connection, run_id: int) -> TestRunDetail:
    run = _get_test_run(conn, run_id)
    results = [_build_result_item(conn, row) for row in _run_llm_calls(conn, run)]
    return TestRunDetail(
        id=run["id"],
        created_at=run["created_at"],
        agent_name=run["agent_name"],
        rubric_id=run["rubric_id"],
        model=run["model"],
        temperature=run["temperature"],
        system_prompt=run["system_prompt"],
        label=run["label"],
        results=results,
    )


@router.post("/test-runs", response_model=TestRunDetail)
def create_test_run(
    payload: TestRunRequest, conn: sqlite3.Connection = Depends(get_db)
) -> TestRunDetail:
    agent_row = get_agent(conn, payload.agent_name)
    if agent_row is None:
        raise HTTPException(status_code=404, detail=f'agent "{payload.agent_name}" לא נמצא.')

    active_rubric = conn.execute("SELECT id FROM rubrics WHERE is_active = 1").fetchone()
    if active_rubric is None:
        raise HTTPException(status_code=404, detail="לא נמצאה רוברייק פעילה.")

    model, system_prompt, temperature = resolve_overrides(
        agent_row, payload.model, payload.system_prompt, payload.temperature
    )

    cursor = conn.execute(
        "INSERT INTO test_runs (created_at, agent_name, rubric_id, model, temperature, "
        "system_prompt, label) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (now_iso(), payload.agent_name, active_rubric["id"], model, temperature, system_prompt, payload.label),
    )
    run_id = cursor.lastrowid
    conn.commit()

    document = load_tax_notes()
    questions = {
        row["id"]: row
        for row in conn.execute(
            "SELECT * FROM test_questions WHERE id IN ({})".format(
                ",".join("?" * len(payload.question_ids))
            ),
            payload.question_ids,
        ).fetchall()
    } if payload.question_ids else {}

    for i, question_id in enumerate(payload.question_ids):
        question_row = questions.get(question_id)
        if question_row is None:
            continue  # question was deleted since the client loaded the list

        if i > 0:
            time.sleep(THROTTLE_SECONDS)

        try:
            # v1 always uses the qa call shape -- see module docstring.
            result = qa.answer(
                document=document,
                question=question_row["question_text"],
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
            )
            log_llm_call(
                conn,
                agent_name=payload.agent_name,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
                question=question_row["question_text"],
                response=result.text,
                latency_ms=result.latency_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                source="test",
                test_run_id=run_id,
            )
        except AgentCallError as e:
            log_llm_call(
                conn,
                agent_name=payload.agent_name,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
                question=question_row["question_text"],
                response=None,
                latency_ms=None,
                input_tokens=None,
                output_tokens=None,
                source="test",
                test_run_id=run_id,
                error=str(e),
            )

    return _build_test_run_detail(conn, run_id)


@router.get("/test-runs", response_model=list[TestRunListItem])
def list_test_runs(conn: sqlite3.Connection = Depends(get_db)) -> list[TestRunListItem]:
    runs = conn.execute("SELECT * FROM test_runs ORDER BY id DESC").fetchall()
    out = []
    for run in runs:
        calls = _run_llm_calls(conn, run)
        scored = 0
        passed = 0
        for call in calls:
            judge_score = conn.execute(
                "SELECT verdict FROM ratings WHERE llm_call_id = ? AND rater = 'judge' AND criterion IS NULL",
                (call["id"],),
            ).fetchone()
            human_score = conn.execute(
                "SELECT verdict FROM ratings WHERE llm_call_id = ? AND rater = 'human' AND criterion IS NULL",
                (call["id"],),
            ).fetchone()
            final = judge_score["verdict"] if judge_score else (human_score["verdict"] if human_score else None)
            if final is not None:
                scored += 1
                if final == "pass":
                    passed += 1
        pass_percentage = round(passed / scored * 100, 1) if scored else None

        out.append(
            TestRunListItem(
                id=run["id"],
                created_at=run["created_at"],
                agent_name=run["agent_name"],
                model=run["model"],
                temperature=run["temperature"],
                label=run["label"],
                pass_percentage=pass_percentage,
            )
        )
    return out


@router.get("/test-runs/{run_id}", response_model=TestRunDetail)
def get_test_run(run_id: int, conn: sqlite3.Connection = Depends(get_db)) -> TestRunDetail:
    return _build_test_run_detail(conn, run_id)


@router.post("/llm-calls/{llm_call_id}/ratings")
def submit_rating(
    llm_call_id: int, payload: RatingRequest, conn: sqlite3.Connection = Depends(get_db)
) -> dict:
    call_row = conn.execute("SELECT * FROM llm_calls WHERE id = ?", (llm_call_id,)).fetchone()
    if call_row is None:
        raise HTTPException(status_code=404, detail="קריאת LLM לא נמצאה.")
    if call_row["test_run_id"] is None:
        raise HTTPException(status_code=400, detail="לא ניתן לדרג קריאה שאינה חלק מריצת בדיקה.")

    run = _get_test_run(conn, call_row["test_run_id"])

    for criterion, verdict in payload.scores.items():
        _upsert_rating(
            conn,
            llm_call_id=llm_call_id,
            rater="human",
            criterion=criterion,
            verdict=verdict,
            explanation=None,
        )

    # Recompute + upsert the criterion=NULL final_score row, merging the
    # programmatic Latency verdict in (humans never rate it via the UI --
    # ResultsTable filters is_programmatic criteria out of its buttons).
    criteria_rows = get_rubric_criteria(conn, run["rubric_id"])
    ratings_dict = {
        r["criterion"]: r["verdict"]
        for r in _ratings_for_call(conn, llm_call_id, "human")
        if r["criterion"] is not None
    }
    for c in criteria_rows:
        if c["is_programmatic"] and call_row["latency_ms"] is not None:
            ratings_dict[c["name"]] = latency_rating(call_row["latency_ms"])

    rubric_row = conn.execute("SELECT * FROM rubrics WHERE id = ?", (run["rubric_id"],)).fetchone()
    final_score = compute_final_score(
        ratings_dict,
        rubric_row["pass_bar_min_good"],
        rubric_row["pass_bar_max_bad"],
        go_no_go_list(conn, run["rubric_id"]),
    )
    _upsert_rating(
        conn, llm_call_id=llm_call_id, rater="human", criterion=None, verdict=final_score, explanation=None
    )
    conn.commit()

    return {"status": "ok", "human_final_score": final_score}


@router.post("/test-runs/{run_id}/judge")
def run_judge(run_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    run = _get_test_run(conn, run_id)

    judge_row = get_agent(conn, "judge")
    if judge_row is None:
        raise HTTPException(status_code=404, detail='agent "judge" לא נמצא.')

    criteria_rows = get_rubric_criteria(conn, run["rubric_id"])
    rubric_row = conn.execute("SELECT * FROM rubrics WHERE id = ?", (run["rubric_id"],)).fetchone()
    go_no_go = go_no_go_list(conn, run["rubric_id"])
    rubric_text = build_rubric_text(criteria_rows)
    document = load_tax_notes()

    # Calls in this run without an existing judge final_score -- idempotent
    # (re-running skips what's already judged).
    to_judge = [
        row
        for row in _run_llm_calls(conn, run)
        if row["response"] is not None
        and conn.execute(
            "SELECT 1 FROM ratings WHERE llm_call_id = ? AND rater = 'judge' AND criterion IS NULL",
            (row["id"],),
        ).fetchone()
        is None
    ]

    judged_count = 0
    for i, call_row in enumerate(to_judge):
        if i > 0:
            time.sleep(THROTTLE_SECONDS)

        try:
            result = judge_agent_module.judge_answer(
                document=document,
                question=call_row["question"],
                answer=call_row["response"],
                rubric_text=rubric_text,
                model=judge_row["default_model"],
                temperature=judge_row["default_temperature"],
            )
        except AgentCallError as e:
            log_llm_call(
                conn,
                agent_name="judge",
                model=judge_row["default_model"],
                temperature=judge_row["default_temperature"],
                system_prompt=judge_row["default_system_prompt"],
                question=f"שיפוט llm_call #{call_row['id']}: {call_row['question']}",
                response=None,
                latency_ms=None,
                input_tokens=None,
                output_tokens=None,
                source="test",
                test_run_id=run_id,
                error=str(e),
            )
            continue

        # llm_calls row B: the judge's own call, kept separate from A (the
        # graded qa call) per plan section 4's explicit clarification.
        log_llm_call(
            conn,
            agent_name="judge",
            model=result.model,
            temperature=result.temperature,
            system_prompt=result.system_prompt,
            question=f"שיפוט llm_call #{call_row['id']}: {call_row['question']}",
            response=result.output.model_dump_json(),
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            source="test",
            test_run_id=run_id,
        )

        ratings_dict: dict[str, str] = {}
        for field_name, criterion_name in _JUDGE_CRITERION_MAP.items():
            criterion_verdict = getattr(result.output, field_name)
            _upsert_rating(
                conn,
                llm_call_id=call_row["id"],
                rater="judge",
                criterion=criterion_name,
                verdict=criterion_verdict.verdict,
                explanation=criterion_verdict.explanation,
            )
            ratings_dict[criterion_name] = criterion_verdict.verdict

        for c in criteria_rows:
            if c["is_programmatic"] and call_row["latency_ms"] is not None:
                latency_verdict = latency_rating(call_row["latency_ms"])
                _upsert_rating(
                    conn,
                    llm_call_id=call_row["id"],
                    rater="judge",
                    criterion=c["name"],
                    verdict=latency_verdict,
                    explanation=None,
                )
                ratings_dict[c["name"]] = latency_verdict

        final_score = compute_final_score(
            ratings_dict, rubric_row["pass_bar_min_good"], rubric_row["pass_bar_max_bad"], go_no_go
        )
        _upsert_rating(
            conn, llm_call_id=call_row["id"], rater="judge", criterion=None, verdict=final_score, explanation=None
        )
        conn.commit()
        judged_count += 1

    return {"status": "ok", "judged_count": judged_count}


@router.get("/test-runs/{run_id}/agreement", response_model=AgreementResponse)
def get_agreement(run_id: int, conn: sqlite3.Connection = Depends(get_db)) -> AgreementResponse:
    run = _get_test_run(conn, run_id)
    calls = _run_llm_calls(conn, run)

    per_criterion_totals: dict[str, dict[str, int]] = {}
    disagreements: list[Disagreement] = []

    for call in calls:
        human_rows = [r for r in _ratings_for_call(conn, call["id"], "human") if r["criterion"] is not None]
        judge_rows = [r for r in _ratings_for_call(conn, call["id"], "judge") if r["criterion"] is not None]
        human_ratings = {r["criterion"]: r["verdict"] for r in human_rows}
        judge_ratings = {r["criterion"]: r["verdict"] for r in judge_rows}
        judge_explanations = {r["criterion"]: (r["explanation"] or "") for r in judge_rows}

        agreement = compute_agreement(human_ratings, judge_ratings)
        question_row = find_question_by_text(conn, call["question"])
        question_text = question_row["question_text"] if question_row else call["question"]

        for criterion, info in agreement["per_criterion"].items():
            totals = per_criterion_totals.setdefault(criterion, {"matches": 0, "total": 0})
            totals["total"] += 1
            if info["match"]:
                totals["matches"] += 1
            else:
                disagreements.append(
                    Disagreement(
                        llm_call_id=call["id"],
                        question_text=question_text,
                        criterion=criterion,
                        human_verdict=info["human"],
                        judge_verdict=info["judge"],
                        judge_explanation=judge_explanations.get(criterion, ""),
                    )
                )

    per_criterion = [
        AgreementPerCriterion(
            criterion=criterion,
            agreement_pct=round(totals["matches"] / totals["total"] * 100, 1) if totals["total"] else 0.0,
            total=totals["total"],
        )
        for criterion, totals in per_criterion_totals.items()
    ]

    return AgreementResponse(per_criterion=per_criterion, disagreements=disagreements)
