"""FastAPI app entrypoint -- CORS, startup DB init/seed, router registration,
and the InvalidInputError -> HTTP 400 exception handler.

Run from the tax-copilot/ root (not from api/) so python-dotenv's .env
loading and the src/ namespace package import both resolve correctly:

    uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.db.connection import get_connection, init_db
from api.db.seed import seed_if_empty
from api.routes import agents, calculate, rag, rubrics, test_questions, test_runs
from src.tax_refund_calculator import InvalidInputError

app = FastAPI(title="Tax Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    conn = get_connection()
    try:
        seed_if_empty(conn)
    finally:
        conn.close()


@app.exception_handler(InvalidInputError)
def invalid_input_handler(request: Request, exc: InvalidInputError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(calculate.router)
app.include_router(agents.router)
app.include_router(rubrics.router)
app.include_router(test_questions.router)
app.include_router(test_runs.router)
app.include_router(rag.router)
