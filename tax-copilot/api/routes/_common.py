"""Shared helpers for api/routes/*.py: per-request DB dependency, agent
default resolution, llm_calls logging, rubric (de)serialization, and
grounding document loading.

Kept inside api/routes/ because the integration task's scope is restricted to
api/schemas.py, api/main.py, and api/routes/ -- this is not a standalone
top-level module, just shared plumbing for the route handlers.
"""

import os
import sqlite3
from datetime import datetime, timezone

from api.db.connection import get_connection

TAX_NOTES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "tax_notes.md"
)


def get_db():
    """FastAPI dependency: a fresh sqlite3 connection per request, closed when
    the request finishes (get_connection() itself is a plain per-call opener,
    not a generator -- this wraps it for proper cleanup)."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def load_tax_notes() -> str:
    with open(TAX_NOTES_PATH, "r", encoding="utf-8") as f:
        return f.read()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_agent(conn: sqlite3.Connection, name: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()


def resolve_overrides(
    agent_row: sqlite3.Row,
    model: str | None,
    system_prompt: str | None,
    temperature: float | None,
) -> tuple[str, str, float]:
    """None fields fall back to the agent's DB-stored defaults -- the server
    resolves this, not just the client (plan section 4)."""
    resolved_model = model if model is not None else agent_row["default_model"]
    resolved_system_prompt = (
        system_prompt if system_prompt is not None else agent_row["default_system_prompt"]
    )
    resolved_temperature = (
        temperature if temperature is not None else agent_row["default_temperature"]
    )
    return resolved_model, resolved_system_prompt, resolved_temperature


def log_llm_call(
    conn: sqlite3.Connection,
    *,
    agent_name: str,
    model: str,
    temperature: float,
    system_prompt: str,
    question: str,
    response: str | None,
    latency_ms: float | None,
    input_tokens: int | None,
    output_tokens: int | None,
    source: str,
    test_run_id: int | None = None,
    error: str | None = None,
) -> int:
    cursor = conn.execute(
        "INSERT INTO llm_calls (created_at, agent_name, model, temperature, system_prompt, "
        "question, response, latency_ms, input_tokens, output_tokens, source, test_run_id, error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            now_iso(),
            agent_name,
            model,
            temperature,
            system_prompt,
            question,
            response,
            latency_ms,
            input_tokens,
            output_tokens,
            source,
            test_run_id,
            error,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_active_rubric_row(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM rubrics WHERE is_active = 1").fetchone()


def get_rubric_criteria(conn: sqlite3.Connection, rubric_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM rubric_criteria WHERE rubric_id = ? ORDER BY sort_order",
        (rubric_id,),
    ).fetchall()


def go_no_go_list(conn: sqlite3.Connection, rubric_id: int) -> list[dict]:
    """scoring.compute_final_score()'s expected go_no_go param shape."""
    rows = conn.execute(
        "SELECT * FROM rubric_go_no_go WHERE rubric_id = ?", (rubric_id,)
    ).fetchall()
    return [
        {
            "criterion": row["criterion"],
            "fails_unless_good": bool(row["fails_unless_good"]),
            "fails_if_bad": bool(row["fails_if_bad"]),
        }
        for row in rows
    ]


def build_rubric_dict(conn: sqlite3.Connection, rubric_row: sqlite3.Row) -> dict:
    """GET/PUT /rubrics/active response shape -- go/no-go merged into each
    criterion object even though it's a separate table in the DB."""
    criteria = get_rubric_criteria(conn, rubric_row["id"])
    go_no_go = {row["criterion"]: row for row in go_no_go_list(conn, rubric_row["id"])}
    criteria_out = []
    for c in criteria:
        gng = go_no_go.get(c["name"])
        criteria_out.append(
            {
                "name": c["name"],
                "good_def": c["good_def"],
                "ok_def": c["ok_def"],
                "bad_def": c["bad_def"],
                "is_programmatic": bool(c["is_programmatic"]),
                "sort_order": c["sort_order"],
                "fails_unless_good": bool(gng["fails_unless_good"]) if gng else False,
                "fails_if_bad": bool(gng["fails_if_bad"]) if gng else False,
            }
        )
    return {
        "name": rubric_row["name"],
        "pass_bar_min_good": rubric_row["pass_bar_min_good"],
        "pass_bar_max_bad": rubric_row["pass_bar_max_bad"],
        "criteria": criteria_out,
    }


def build_rubric_text(criteria_rows: list[sqlite3.Row]) -> str:
    """Human-readable rubric text for judge.judge_answer()'s rubric_text param.
    Excludes the is_programmatic criterion (Latency) -- it's never sent to the
    judge, only rated programmatically via scoring.latency_rating()."""
    lines = []
    for c in criteria_rows:
        if c["is_programmatic"]:
            continue
        lines.append(
            f"- {c['name']}:\n"
            f"  good: {c['good_def']}\n"
            f"  ok: {c['ok_def']}\n"
            f"  bad: {c['bad_def']}"
        )
    return "\n".join(lines)


def questions_by_text(conn: sqlite3.Connection, texts: list[str]) -> dict[str, sqlite3.Row]:
    """Batch form of matching llm_calls.question (verbatim question_text sent,
    see routes/test_runs.py) back to its test_questions row -- llm_calls has
    no question_id FK, so text match is the only available linkage."""
    if not texts:
        return {}
    placeholders = ",".join("?" * len(texts))
    rows = conn.execute(
        f"SELECT * FROM test_questions WHERE question_text IN ({placeholders})",
        texts,
    ).fetchall()
    return {row["question_text"]: row for row in rows}


def ratings_by_call(conn: sqlite3.Connection, call_ids: list[int]) -> dict[int, list[sqlite3.Row]]:
    """All ratings rows for a batch of llm_call_ids, grouped by llm_call_id --
    avoids one query per call when building results for a whole test run."""
    if not call_ids:
        return {}
    placeholders = ",".join("?" * len(call_ids))
    rows = conn.execute(
        f"SELECT * FROM ratings WHERE llm_call_id IN ({placeholders})",
        call_ids,
    ).fetchall()
    out: dict[int, list[sqlite3.Row]] = {call_id: [] for call_id in call_ids}
    for row in rows:
        out[row["llm_call_id"]].append(row)
    return out
