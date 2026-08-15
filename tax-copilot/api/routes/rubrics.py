"""GET/PUT /rubrics/active.

PUT never mutates an existing rubric's rows in place -- it always inserts a
new rubrics + rubric_criteria + rubric_go_no_go version and flips is_active,
so test_runs.rubric_id keeps pointing at the exact version that was active
when that run happened (plan section 3).
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from api.routes._common import build_rubric_dict, get_active_rubric_row, now_iso, get_db
from api.schemas import RubricIO

router = APIRouter()


@router.get("/rubrics/active", response_model=RubricIO)
def get_active_rubric(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    rubric_row = get_active_rubric_row(conn)
    if rubric_row is None:
        raise HTTPException(status_code=404, detail="לא נמצאה רוברייק פעילה.")
    return build_rubric_dict(conn, rubric_row)


@router.put("/rubrics/active", response_model=RubricIO)
def put_active_rubric(
    payload: RubricIO, conn: sqlite3.Connection = Depends(get_db)
) -> dict:
    cursor = conn.execute(
        "INSERT INTO rubrics (name, is_active, pass_bar_min_good, pass_bar_max_bad, created_at) "
        "VALUES (?, 0, ?, ?, ?)",
        (payload.name, payload.pass_bar_min_good, payload.pass_bar_max_bad, now_iso()),
    )
    new_rubric_id = cursor.lastrowid

    for sort_order, criterion in enumerate(payload.criteria):
        conn.execute(
            "INSERT INTO rubric_criteria "
            "(rubric_id, name, good_def, ok_def, bad_def, is_programmatic, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                new_rubric_id,
                criterion.name,
                criterion.good_def,
                criterion.ok_def,
                criterion.bad_def,
                int(criterion.is_programmatic),
                criterion.sort_order,
            ),
        )
        if criterion.fails_unless_good or criterion.fails_if_bad:
            conn.execute(
                "INSERT INTO rubric_go_no_go (rubric_id, criterion, fails_unless_good, fails_if_bad) "
                "VALUES (?, ?, ?, ?)",
                (
                    new_rubric_id,
                    criterion.name,
                    int(criterion.fails_unless_good),
                    int(criterion.fails_if_bad),
                ),
            )

    conn.execute("UPDATE rubrics SET is_active = 0")
    conn.execute("UPDATE rubrics SET is_active = 1 WHERE id = ?", (new_rubric_id,))
    conn.commit()

    new_row = conn.execute("SELECT * FROM rubrics WHERE id = ?", (new_rubric_id,)).fetchone()
    return build_rubric_dict(conn, new_row)
