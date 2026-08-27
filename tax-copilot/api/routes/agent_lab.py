"""מטלה 4 -- Agent Lab endpoints. שם נפרד מ-`api/routes/agents.py` הקיים (מטלה 2,
LLM-writer configs) בכוונה -- ראו api/agentlab/__init__.py.

FREE (0 קריאות LLM, קריאה מהדיסק/זיכרון):
    GET /agent-lab/tools          GET /agent-lab/tasks
    GET /agent-lab/configs        POST /agent-lab/configs      DELETE /agent-lab/configs/{id}
    GET /agent-lab/matrix         GET /agent-lab/experiments    GET /agent-lab/annotated-traces
    GET /agent-lab/cost

עולה קריאות LLM:
    POST /agent-lab/run   קריאה בודדת (RAG) עד כמה (agent multi-hop + evaluator-optimizer)
"""

from fastapi import APIRouter, HTTPException

from api.agentlab import runner
from api.agentlab_schemas import AddConfigRequest, RunRequest

router = APIRouter(prefix="/agent-lab", tags=["agent-lab"])


@router.get("/tools")
def get_tools() -> dict:
    return {"tools": runner.list_tools()}


@router.get("/tasks")
def get_tasks() -> dict:
    return {"tasks": runner.list_tasks()}


@router.post("/run")
def post_run(payload: RunRequest) -> dict:
    try:
        return runner.run_single(
            payload.task, payload.config, enabled_tools=payload.enabled_tools,
            break_tool=payload.break_tool, use_evaluator_optimizer=payload.use_evaluator_optimizer,
            model=payload.model, judge_model=payload.judge_model, system_prompt=payload.system_prompt,
        )
    except Exception as exc:  # noqa: BLE001 -- שגיאת agent/RAG אמיתית מוחזרת כ-400, לא 500 גנרי
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/configs")
def get_configs() -> dict:
    return {"configs": runner.list_configs()}


@router.post("/configs")
def post_config(payload: AddConfigRequest) -> dict:
    return runner.add_config(payload.name, payload.model, payload.judge_model,
                              payload.enabled_tools, payload.system_prompt)


@router.delete("/configs/{config_id}", status_code=204)
def delete_config(config_id: str):
    if config_id == "canonical":
        raise HTTPException(status_code=400, detail="לא ניתן למחוק את הקונפיגורציה הקנונית.")
    if not runner.delete_config(config_id):
        raise HTTPException(status_code=404, detail="קונפיגורציה לא נמצאה.")
    return None


@router.get("/matrix")
def get_matrix() -> dict:
    return runner.get_matrix_results()


@router.get("/experiments")
def get_experiments() -> dict:
    return runner.get_experiments()


@router.get("/annotated-traces")
def get_annotated_traces() -> dict:
    return runner.get_annotated_traces()


@router.get("/cost")
def get_cost() -> dict:
    return runner.get_cost()
