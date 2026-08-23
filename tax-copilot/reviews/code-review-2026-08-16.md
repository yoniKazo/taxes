# /code-review — 2026-08-16, browser client working diff

**S3.** Run on the working diff that added the React + FastAPI browser client (calculator + AI Test Lab), before opening a PR. Fixes landed in commit `825c2c0`.

## Findings

| # | Finding | Outcome |
|---|---|---|
| 1 | `pension_employee_pct` sent to the API as a raw percent (e.g. `6`) instead of a fraction — read back as 600%. | **Fixed** |
| 2 | `gross_salary` was being treated as a monthly figure in the UI; the calculator expects annual and converts internally. | **Fixed** — input now entered as annual, converted to monthly before `calculate()`. |
| 3 | Test Lab's `agent_name="judge"` collided with the judge's own internal LLM-call bookkeeping, corrupting call counts. | **Fixed** |
| 4 | `call_text`/`call_structured` crashed with no handling when the LLM response content was `None`. | **Fixed** |
| 5 | `test_questions` DELETE was a hard delete, breaking historical lookups for test runs that referenced the deleted question. | **Fixed** — soft delete. |
| 6 | N+1 query pattern in `list_test_runs`, `_build_test_run_detail`, and `get_agreement`. | **Fixed** |
| 7 | Dead error-handling branch for agent rows that are always seeded at startup and can never be missing. | **Fixed** — removed (per `CLAUDE.md`: no error handling for scenarios that can't happen). |
| 8 | Over-long docstrings and an unused `DEFAULT_SYSTEM_PROMPT` constant. | **Fixed** — trimmed/removed (per `CLAUDE.md`: no docstrings beyond a line where the name doesn't already say it). |

**Nothing was rejected.** All 8 findings were fixed in `825c2c0`. Findings #7 and #8 are notable for being *removals* rather than additions — the review caught the diff violating this project's own `CLAUDE.md` conventions, not just introducing bugs.
