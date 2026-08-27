"""מטלה 4 -- לוגיקת ה-API: tools/tasks/הרצה בודדת/קונפיגורציות/תוצאות מטריצה.

הרצה בודדת (RAG או Agent) חוסמת בקשה אחת (כמה שניות עד כ-30 שניות ל-agent
multi-hop) -- לא job, בניגוד למטריצה המלאה (Task 5, מורצת מה-CLI כמו assignment3,
לא דרך ה-API, כי אלה מאות קריאות בתשלום אמיתי; ה-API רק *קורא* את התוצאות
השמורות, כמו artifacts.py של ה-RAG lab).

קונפיגורציות ה-agent (Task 6, "מנהל קונפיגורציות") הן in-memory בכוונה, אותו
דפוס בדיוק כמו api/jobs.py: אפליקציה חד-משתמשית מקומית, בלי DB migration
נוספת -- לא נשרדות restart, וזו מגבלה מקובלת לא פספוס.
"""

import itertools
import os
import threading
import time
import uuid
from dataclasses import asdict
from typing import Any

import pandas as pd

from agent import DEFAULT_TOOLS, broken_tools, run_agent_task
from agent_tracing import RunSummary, SafetyNets, StepRecord
from build_index import load_index
from evaluator_optimizer import run_with_evaluator_optimizer
from rag_pipeline import answer_with_rag_instrumented

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TASKS_PATH = os.path.join(REPO_ROOT, "assignment4", "data", "tasks.csv")
XLSX_PATH = os.path.join(REPO_ROOT, "assignment4", "assignment_04.xlsx")
EXPERIMENTS_PATH = os.path.join(REPO_ROOT, "assignment4", "data", "experiments.json")
ANNOTATED_DIR = os.path.join(REPO_ROOT, "assignment4", "annotated_traces")

_TOOLS_BY_NAME = {t.name: t for t in DEFAULT_TOOLS}
_vectorstore = None
_lock = threading.Lock()


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = load_index()
    return _vectorstore


class ListTracer:
    """כמו agent_tracing.JsonlTracer, אבל לרשימה בזיכרון -- נוח להחזרה ישירה
    ב-response של הרצה בודדת, בלי לקרוא קובץ אחרי הכתיבה."""

    def __init__(self):
        self.steps: list[dict] = []
        self.summary: dict | None = None

    def write_step(self, record: StepRecord) -> None:
        self.steps.append(asdict(record))

    def write_summary(self, summary: RunSummary) -> None:
        self.summary = asdict(summary)


def list_tools() -> list[dict]:
    out = []
    for t in DEFAULT_TOOLS:
        schema = t.args_schema.model_json_schema()
        out.append({
            "name": t.name,
            "description": t.description,
            "properties": schema.get("properties", {}),
            "required": schema.get("required", []),
        })
    return out


def list_tasks() -> list[dict]:
    df = pd.read_csv(TASKS_PATH)
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")


def run_single(
    task: str, config: str, *, enabled_tools: list[str] | None = None,
    break_tool: str | None = None, use_evaluator_optimizer: bool = True,
    model: str = "claude-haiku-4-5", judge_model: str = "claude-sonnet-5",
    system_prompt: str | None = None,
) -> dict:
    """config: "rag" | "agent". enabled_tools: תת-קבוצה של שמות ה-3 tools
    (None = כולם). break_tool: שם tool שנשבר בכוונה (Task 3.5 המחשה)."""
    if config == "rag":
        parsed, meta = answer_with_rag_instrumented(task, vectorstore=_get_vectorstore())
        return {
            "config": "rag", "answer": parsed.answer,
            "terminal_state": "answered" if parsed.answered else "refused",
            "sources": parsed.sources, "steps": [], "tool_calls": 1,
            "latency_ms": meta["latency_ms"], "input_tokens": meta["input_tokens"],
            "output_tokens": meta["output_tokens"],
        }

    tools = [_TOOLS_BY_NAME[name] for name in enabled_tools] if enabled_tools else list(DEFAULT_TOOLS)
    if break_tool:
        # broken_tools() מחזירה תמיד את שלושת ה-tools בסדר DEFAULT_TOOLS עם אחד שבור --
        # לבחור לפי שם, לא לפי אינדקס (אינדקס 0 היה תלוי-מזל באיזה tool בדיוק נשבר).
        broken_by_name = {t.name: t for t in broken_tools(break_tool)}
        tools = [broken_by_name[t.name] if t.name == break_tool else t for t in tools]
    tracer = ListTracer()

    if use_evaluator_optimizer:
        result = run_with_evaluator_optimizer(task, task_id="playground", run=1, tools=tools, tracer=tracer,
                                               model=model, judge_model=judge_model, system_prompt=system_prompt)
        summary = result["summary"]
        judge_info = {"verdict": result["verdict"], "ratings": result["ratings"], "rounds": result["rounds_used"]}
    else:
        summary = run_agent_task(task, task_id="playground", run=1, tools=tools, tracer=tracer,
                                  model=model, system_prompt=system_prompt)
        judge_info = None

    record_usage(model, summary.total_input_tokens, summary.total_output_tokens)
    if use_evaluator_optimizer:
        # קריאות ה-judge (Sonnet) ל-evaluator-optimizer לא נספרות בטוקנים כאן --
        # run_with_evaluator_optimizer לא מחזיר את usage שלהן כרגע; ה-chip מדווח
        # את עלות ה-agent (Haiku) בלבד, לא claim מלא. פער ידוע, לא סוד.
        pass
    return {
        "config": "agent", "answer": summary.answer, "terminal_state": summary.terminal_state,
        "steps": tracer.steps, "tool_calls": summary.tool_calls, "tools_used": summary.tools_used,
        "latency_ms": summary.total_wall_ms, "input_tokens": summary.total_input_tokens,
        "output_tokens": summary.total_output_tokens, "judge": judge_info,
    }


# --- agent configurations (in-memory, Task 6's "add/remove agents for testing") ---

_configs: dict[str, dict] = {}
_id_counter = itertools.count(1)


def _canonical_config() -> dict:
    return {
        "id": "canonical", "name": "קנונית (ברירת מחדל, Task 3/4)", "model": "claude-haiku-4-5",
        "judge_model": "claude-sonnet-5",
        "enabled_tools": [t.name for t in DEFAULT_TOOLS], "system_prompt": None, "is_canonical": True,
    }


def list_configs() -> list[dict]:
    with _lock:
        return [_canonical_config(), *_configs.values()]


def add_config(name: str, model: str, judge_model: str, enabled_tools: list[str],
               system_prompt: str | None) -> dict:
    config_id = f"cfg-{next(_id_counter)}-{uuid.uuid4().hex[:6]}"
    config = {"id": config_id, "name": name, "model": model, "judge_model": judge_model,
               "enabled_tools": enabled_tools, "system_prompt": system_prompt,
               "is_canonical": False, "created_at": time.time()}
    with _lock:
        _configs[config_id] = config
    return config


def delete_config(config_id: str) -> bool:
    with _lock:
        return _configs.pop(config_id, None) is not None


def get_config(config_id: str) -> dict | None:
    if config_id == "canonical":
        return _canonical_config()
    with _lock:
        return _configs.get(config_id)


# --- reading finished artifacts (Task 5 matrix, Task 6 experiments, annotated traces) ---


_NA_STRING_COLS = ["answer", "success", "refused", "terminal_state",
                   "faithfulness_verdict", "refusal_correctness"]
# NOT here on purpose: tools_used ("[]") and faithfulness_explanation (a real sentence,
# "structurally meaningless for RAG -- no tool concept") were never literally "n/a" in
# assignment4_eval_runner.run_rag_row, so they survive the Excel round-trip untouched --
# blanket-overwriting them with "n/a" would destroy real, more informative content.


def get_matrix_results() -> dict:
    if not os.path.exists(XLSX_PATH):
        return {"available": False, "rows": [], "summary": {}}
    # Plain read_excel (default NA handling): needed so genuinely-blank numeric
    # cells (latency_ms/input_tokens/... on n/a rows) parse as real NaN, not the
    # empty string -- keep_default_na=False (an earlier version of this fix)
    # broke exactly that, and crashed .mean() with "Could not convert string ''".
    # The "structurally meaningless for RAG" marker is re-derived from the known
    # condition (config=rag, type in no_tool/tool_fails) instead of depending on
    # the literal string "n/a" surviving an Excel round-trip.
    df = pd.read_excel(XLSX_PATH)
    na_mask = (df["config"] == "rag") & (df["type"].isin(["no_tool", "tool_fails"]))
    # astype(object) first: a column pandas inferred as bool/float64 (e.g. `refused`,
    # all True/False/NaN before this point) raises TypeError on assigning the string
    # "n/a" directly -- casting to object makes every column string-safe regardless
    # of what dtype read_excel happened to infer.
    for col in _NA_STRING_COLS:
        df[col] = df[col].astype(object)
    df.loc[na_mask, _NA_STRING_COLS] = "n/a"
    df_display = df.where(pd.notnull(df), None)

    def rate(sub: pd.DataFrame) -> float | None:
        vals = sub["success"].tolist()
        countable = [v for v in vals if v in ("good", "ok", "bad")]
        if not countable:
            return None
        return sum(1 for v in countable if v == "good") / len(countable)

    summary = []
    for (task_type, cfg), group in df.groupby(["type", "config"]):
        summary.append({
            "type": task_type, "config": cfg, "n": len(group),
            "success_rate": rate(group),
            "mean_latency_ms": group["latency_ms"].dropna().mean() if group["latency_ms"].notna().any() else None,
            "mean_tool_calls": group["tool_calls"].dropna().mean() if group["tool_calls"].notna().any() else None,
        })
    return {"available": True, "rows": df_display.to_dict(orient="records"), "summary": summary}


def get_experiments() -> dict:
    if not os.path.exists(EXPERIMENTS_PATH):
        return {"available": False, "experiments": []}
    import json
    with open(EXPERIMENTS_PATH, encoding="utf-8") as f:
        return {"available": True, "experiments": json.load(f)}


def get_annotated_traces() -> dict:
    if not os.path.isdir(ANNOTATED_DIR):
        return {"available": False, "traces": []}
    traces = []
    for name in sorted(os.listdir(ANNOTATED_DIR)):
        if name.endswith(".md"):
            with open(os.path.join(ANNOTATED_DIR, name), encoding="utf-8") as f:
                traces.append({"name": name, "content": f.read()})
    return {"available": bool(traces), "traces": traces}


# --- session cost (mirrors ProviderUsage.cost_usd pricing from agent_team.py) ---

_ANTHROPIC_PRICING = {
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    "claude-sonnet-5": {"input": 3.0, "output": 15.0},
}
_session_usage = {"claude-haiku-4-5": [0, 0], "claude-sonnet-5": [0, 0]}


def record_usage(model: str, input_tokens: int, output_tokens: int) -> None:
    with _lock:
        bucket = _session_usage.setdefault(model, [0, 0])
        bucket[0] += input_tokens
        bucket[1] += output_tokens


def get_cost() -> dict:
    with _lock:
        breakdown = {}
        total = 0.0
        for model, (input_tokens, output_tokens) in _session_usage.items():
            rates = _ANTHROPIC_PRICING.get(model, {"input": 0, "output": 0})
            cost = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
            breakdown[model] = {"input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": round(cost, 4)}
            total += cost
        return {"total_usd": round(total, 4), "by_model": breakdown}
