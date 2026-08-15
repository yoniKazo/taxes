"""GET /agents."""

import sqlite3

from fastapi import APIRouter, Depends

from api.routes._common import get_db
from api.schemas import AgentOut

router = APIRouter()


@router.get("/agents", response_model=list[AgentOut])
def list_agents(conn: sqlite3.Connection = Depends(get_db)) -> list[AgentOut]:
    rows = conn.execute("SELECT * FROM agents ORDER BY id").fetchall()
    return [
        AgentOut(
            name=row["name"],
            description=row["description"],
            default_model=row["default_model"],
            default_system_prompt=row["default_system_prompt"],
            default_temperature=row["default_temperature"],
        )
        for row in rows
    ]
