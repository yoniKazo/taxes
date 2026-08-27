"""מטלה 4, Task 5: המטריצה. קונפיגורציה A = RAG הקפוא של מטלה 3 (commit 39692df,
answer_with_rag_instrumented ללא שינוי). קונפיגורציה B = agent + evaluator-optimizer
(Task 4). 5 הרצות לכל משימה בכל קונפיגורציה. no_tool/tool_fails הם n/a עבור RAG
(structurally meaningless -- נרשם כך במפורש, לא מושמט).

4 מכשירי מדידה נפרדים (ראו plans/assignment4-plan.md): task success (קוד קודם,
Sonnet רק כ-fallback ל-success_criteria פתוח), faithfulness (Sonnet מול tool_outputs
ל-agent, judges.py הקיים מול צ'אנקים ל-RAG), refusal correctness (קוד בלבד),
trajectory sanity (דיבאג בלבד, לא כאן -- ראו assignment4_analysis.py).
"""

import json
import os
import re
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from agent import broken_tools  # noqa: E402
from agent_tracing import JsonlTracer  # noqa: E402
from assignment4_judges import judge_faithfulness as judge_faithfulness_agent  # noqa: E402
from assignment4_judges import judge_task_success, refusal_correctness  # noqa: E402
from build_index import load_index  # noqa: E402
from evaluator_optimizer import run_with_evaluator_optimizer  # noqa: E402
from judges import judge_faithfulness as judge_faithfulness_rag  # noqa: E402
from rag_pipeline import answer_with_rag_instrumented  # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_PATH = os.path.join(SCRIPT_DIR, "..", "assignment4", "data", "tasks.csv")
TRACE_DIR = os.path.join(SCRIPT_DIR, "..", "assignment4", "data", "traces")
XLSX_PATH = os.path.join(SCRIPT_DIR, "..", "assignment4", "assignment_04.xlsx")
N_RUNS = 5

FROZEN_BASELINE_COMMIT = "39692df"  # ראו plans/assignment4-plan.md


def load_tasks() -> pd.DataFrame:
    return pd.read_csv(TASKS_PATH)


def score_task_success(row: pd.Series, answer: str, tool_calls: int, terminal_state: str) -> tuple[str, str]:
    """בדיקת-קוד תמיד קודם ל-success_criteria הספציפי של השורה; שופט Sonnet הוא
    fallback בלבד לשורות שה-predicate שלהן פתוח מהותית (אין כאלה במערך הנוכחי --
    24/24 המשימות נבנו code-checkable בכוונה)."""
    sc = str(row["success_criteria"])
    answer = answer or ""

    m = re.search(r"tool_calls\s*==\s*(\d+)", sc)
    if m and "refused" not in sc:
        ok = tool_calls == int(m.group(1))
        return ("good" if ok else "bad"), f"tool_calls={tool_calls}, נדרש =={m.group(1)}"

    if "refused == True" in sc:
        refused = terminal_state == "refused"
        m2 = re.search(r"tool_calls\s*<=\s*(\d+)", sc)
        ok = refused and (tool_calls <= int(m2.group(1)) if m2 else True)
        return ("good" if ok else "bad"), f"refused={refused}, tool_calls={tool_calls}"

    quoted = re.findall(r'"([^"]+)"', sc)
    if quoted:
        norm_answer = answer.replace(",", "")
        ok = any(q.replace(",", "") in norm_answer for q in quoted)
        return ("good" if ok else "bad"), f'בדק הכלת {quoted} בתשובה'

    verdict = judge_task_success(row["task"], sc, answer)
    return verdict.verdict, verdict.explanation


def run_rag_row(row: pd.Series, run_idx: int, vectorstore) -> dict:
    if row["type"] in ("no_tool", "tool_fails"):
        return {
            "config": "rag", "run": run_idx, "answer": "n/a", "success": "n/a", "refused": "n/a",
            "terminal_state": "n/a", "tool_calls": 0, "tools_used": "[]", "steps": 0,
            "faithfulness_verdict": "n/a",
            "faithfulness_explanation": "structurally meaningless for RAG -- no tool concept",
            "latency_ms": None, "input_tokens": None, "output_tokens": None,
        }

    parsed, meta = answer_with_rag_instrumented(row["task"], vectorstore=vectorstore)
    terminal_state = "answered" if parsed.answered else "refused"
    success_verdict, _ = score_task_success(row, parsed.answer, tool_calls=1, terminal_state=terminal_state)
    faith = judge_faithfulness_rag(parsed.answer, meta["retrieved_texts"], row["task"])

    return {
        "config": "rag", "run": run_idx, "answer": parsed.answer, "success": success_verdict,
        "refused": not parsed.answered, "terminal_state": terminal_state, "tool_calls": 1,
        "tools_used": "['search_tax_corpus']", "steps": 1,
        "faithfulness_verdict": faith.verdict, "faithfulness_explanation": faith.explanation,
        "latency_ms": meta["latency_ms"], "input_tokens": meta["input_tokens"],
        "output_tokens": meta["output_tokens"],
    }


def run_agent_row(row: pd.Series, run_idx: int, tracer: JsonlTracer, *,
                   agent_model: str = "claude-haiku-4-5", judge_model: str = "claude-sonnet-5") -> dict:
    """agent_model/judge_model: ברירת המחדל היא הקונפיגורציה הקנונית של המטלה
    (src/model_providers.py) -- דגלי CLI מאפשרים ריצת-חקירה זולה עם Gemini, אבל
    הריצה הרשמית של Task 5 (שהמטלה בפועל דורשת) נשארת Claude."""
    tools = None
    break_tool = row.get("break_tool")
    if row["type"] == "tool_fails" and isinstance(break_tool, str) and break_tool:
        tools = broken_tools(break_tool)

    result = run_with_evaluator_optimizer(row["task"], task_id=str(row["task_id"]), run=run_idx,
                                           tools=tools, tracer=tracer, model=agent_model, judge_model=judge_model)
    summary = result["summary"]
    success_verdict, _ = score_task_success(row, summary.answer, summary.tool_calls, summary.terminal_state)

    if summary.terminal_state in ("cap_breached", "error"):
        faith_verdict, faith_expl = "n/a", f"אין תשובה לשפוט (terminal_state={summary.terminal_state})"
    else:
        faith = judge_faithfulness_agent(row["task"], summary.tool_outputs, summary.answer, model=judge_model)
        faith_verdict, faith_expl = faith.verdict, faith.explanation

    return {
        "config": "agent", "run": run_idx, "answer": summary.answer, "success": success_verdict,
        "refused": summary.terminal_state == "refused", "terminal_state": summary.terminal_state,
        "tool_calls": summary.tool_calls, "tools_used": str(summary.tools_used), "steps": summary.steps,
        "faithfulness_verdict": faith_verdict, "faithfulness_explanation": faith_expl,
        "latency_ms": summary.total_wall_ms, "input_tokens": summary.total_input_tokens,
        "output_tokens": summary.total_output_tokens,
    }


CHECKPOINT_PATH = os.path.join(SCRIPT_DIR, "..", "assignment4", "data", "matrix_checkpoint.jsonl")


def _load_checkpoint(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _append_checkpoint(path: str, row: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_matrix(n_runs: int = N_RUNS, task_filter: list[str] | None = None,
               progress: bool = True, checkpoint_path: str = CHECKPOINT_PATH,
               resume: bool = True, configs: set[str] = frozenset({"rag", "agent"}),
               agent_model: str = "claude-haiku-4-5", judge_model: str = "claude-sonnet-5") -> pd.DataFrame:
    """כותב כל שורה (RAG ו-agent) ל-checkpoint ב-JSONL **מיד** אחרי שהיא מחושבת --
    לא רק ל-xlsx בסוף. ריצה שנקטעת (קרדיט, רשת, כל דבר) לא מוחקת עבודה ששולמה
    עליה כבר; resume=True מדלג על (task_id, run, config) שכבר ב-checkpoint.
    בדיוק הלקח מ-CLAUDE.md CODIFY 2026-08-19 (מטלה 3, Task 6) -- שנלמד שוב כאן
    ביוקר, אחרי שריצת Task 5 המלאה נקטעה באמצע מ-'Your credit balance is too low'."""
    tasks = load_tasks()
    if task_filter is not None:
        tasks = tasks[tasks["task_id"].isin(task_filter)]
    vectorstore = load_index()  # פעם אחת, לא בכל שורה

    done = _load_checkpoint(checkpoint_path) if resume else []
    done_keys = {(r["task_id"], r["run"], r["config"]) for r in done}
    rows = list(done)
    if done_keys:
        print(f"  ({len(done_keys)} שורות כבר ב-checkpoint, מדלג עליהן)")

    for _, task_row in tasks.iterrows():
        task_id = task_row["task_id"]
        answerable = bool(task_row["answerable"]) if not isinstance(task_row["answerable"], str) \
            else task_row["answerable"].strip().lower() == "true"
        tracer = JsonlTracer(os.path.join(TRACE_DIR, f"{task_id}.jsonl"))
        for run_idx in range(1, n_runs + 1):
            base = {
                "task_id": task_id, "task": task_row["task"], "type": task_row["type"],
                "answerable": answerable, "success_criteria": task_row["success_criteria"],
            }
            t0 = time.perf_counter()

            rag_row = agent_row = None
            if "rag" in configs:
                if (task_id, run_idx, "rag") not in done_keys:
                    rag_row = run_rag_row(task_row, run_idx, vectorstore)
                    rag_row["refusal_correctness"] = (
                        "n/a" if rag_row["terminal_state"] == "n/a"
                        else refusal_correctness(answerable, rag_row["terminal_state"])
                    )
                    full_rag_row = {**base, **rag_row}
                    rows.append(full_rag_row)
                    _append_checkpoint(checkpoint_path, full_rag_row)
                else:
                    rag_row = next(r for r in done if r["task_id"] == task_id and r["run"] == run_idx and r["config"] == "rag")

            if "agent" in configs:
                if (task_id, run_idx, "agent") not in done_keys:
                    agent_row = run_agent_row(task_row, run_idx, tracer,
                                               agent_model=agent_model, judge_model=judge_model)
                    agent_row["refusal_correctness"] = refusal_correctness(answerable, agent_row["terminal_state"])
                    full_agent_row = {**base, **agent_row}
                    rows.append(full_agent_row)
                    _append_checkpoint(checkpoint_path, full_agent_row)
                else:
                    agent_row = next(r for r in done if r["task_id"] == task_id and r["run"] == run_idx and r["config"] == "agent")

            if progress:
                dt = round(time.perf_counter() - t0, 1)
                rag_part = f"rag={rag_row['success']}/{rag_row['terminal_state']}" if rag_row else "rag=skipped"
                agent_part = f"agent={agent_row['success']}/{agent_row['terminal_state']}" if agent_row else "agent=skipped"
                print(f"  {task_id} run {run_idx}/{n_runs} ({dt}s): {rag_part} | {agent_part}")
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", nargs="*", default=None, help="task_id subset, e.g. --tasks s2 mh1 nt1")
    parser.add_argument("--runs", type=int, default=N_RUNS)
    parser.add_argument("--out", default=XLSX_PATH)
    parser.add_argument("--configs", nargs="*", default=["rag", "agent"], choices=["rag", "agent"],
                         help="להריץ רק צד אחד -- שימושי כשה-Anthropic credit נגמר וה-RAG (Gemini) עדיין זמין")
    parser.add_argument("--no-resume", action="store_true", help="להתעלם מה-checkpoint ולהריץ הכל מחדש")
    parser.add_argument("--agent-model", default="claude-haiku-4-5",
                         help="ברירת המחדל היא הקנונית של המטלה; ריצת-חקירה זולה: gemini-flash-lite-latest. "
                              "הריצה הרשמית של Task 5 נשארת עם ברירת המחדל.")
    parser.add_argument("--judge-model", default="claude-sonnet-5",
                         help="ברירת המחדל היא הקנונית של המטלה; ריצת-חקירה זולה: gemini-3.1-flash-lite.")
    args = parser.parse_args()

    print(f"baseline קפוא: commit {FROZEN_BASELINE_COMMIT}")
    df = run_matrix(n_runs=args.runs, task_filter=args.tasks, resume=not args.no_resume,
                     configs=frozenset(args.configs), agent_model=args.agent_model, judge_model=args.judge_model)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_excel(args.out, index=False)
    print(f"\n{len(df)} שורות נכתבו ל-{os.path.abspath(args.out)}")
