"""GET/POST /test-questions, DELETE /test-questions/{id}."""

import sqlite3

from fastapi import APIRouter, Depends, Response

from api.routes._common import get_db
from api.schemas import TestQuestionIn, TestQuestionOut

router = APIRouter()


def _to_out(row: sqlite3.Row) -> TestQuestionOut:
    return TestQuestionOut(
        id=row["id"],
        dataset_name=row["dataset_name"],
        category=row["category"],
        question_text=row["question_text"],
        is_active=bool(row["is_active"]),
    )


@router.get("/test-questions", response_model=list[TestQuestionOut])
def list_test_questions(
    dataset: str = "tax_qa_v1", conn: sqlite3.Connection = Depends(get_db)
) -> list[TestQuestionOut]:
    rows = conn.execute(
        "SELECT * FROM test_questions WHERE dataset_name = ? AND is_active = 1 ORDER BY id",
        (dataset,),
    ).fetchall()
    return [_to_out(row) for row in rows]


@router.post("/test-questions", response_model=TestQuestionOut)
def create_test_question(
    payload: TestQuestionIn, conn: sqlite3.Connection = Depends(get_db)
) -> TestQuestionOut:
    cursor = conn.execute(
        "INSERT INTO test_questions (dataset_name, category, question_text, is_active) "
        "VALUES (?, ?, ?, 1)",
        (payload.dataset_name, payload.category, payload.question_text),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM test_questions WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _to_out(row)


@router.delete("/test-questions/{question_id}", status_code=204)
def delete_test_question(
    question_id: int, conn: sqlite3.Connection = Depends(get_db)
) -> Response:
    # Soft delete -- keeps the row so questions_by_text can still recover
    # question_id for llm_calls rows logged against this question in past
    # test runs; is_active=0 just excludes it from future runs' checklists.
    conn.execute("UPDATE test_questions SET is_active = 0 WHERE id = ?", (question_id,))
    conn.commit()
    return Response(status_code=204)
