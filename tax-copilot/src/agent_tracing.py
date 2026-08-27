"""מטלה 4: tracer משותף ל-JSONL + קונפיגורציית רשתות-הביטחון, בשימוש agent.py
ו-assignment4_eval_runner.py (ולא raw_loop.py -- זה כבר רץ בלי tracing, פעם אחת,
ולא ייגע בו שוב).

חוזה ה-trace: שורת JSONL אחת לכל צעד (thought/tool/input/output/duration/tokens),
ועוד שורת סיכום אחת בסוף כל הרצה. terminal_state הוא בדיוק אחד מ-TERMINAL_STATES --
זה השדה שמוזן לעמודת terminal_state ב-assignment_04.xlsx.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

TERMINAL_STATES = ("answered", "refused", "cap_breached", "error")

# תואם לדפוס REFUSAL_SENTENCE הקיים ב-rag_pipeline.py: מחרוזת סירוב קבועה
# שה-system prompt מחייב, כדי שסיווג "refused" יהיה בדיקת-מחרוזת ולא ניחוש.
REFUSAL_MARKER = "לא מצאתי את זה במסמכים או בכלים הזמינים."


@dataclass
class StepRecord:
    task_id: str
    run: int
    step: int
    thought: str
    tool: str | None
    input: dict | None
    output: str | None
    duration_ms: float
    input_tokens: int
    output_tokens: int


@dataclass
class RunSummary:
    task_id: str
    run: int
    steps: int
    total_input_tokens: int
    total_output_tokens: int
    total_wall_ms: float
    terminal_state: str
    tool_calls: int
    tools_used: list[str]
    answer: str
    breach: str | None = None
    # כל פלטי ה-tools מההרצה, מחוברים -- זה מה ש-faithfulness (Task 5) ו-
    # evaluator-optimizer (Task 4) שופטים מולו, לא רק צ'אנקי אחזור כמו במטלה 3.
    tool_outputs: str = ""


class JsonlTracer:
    """כותב append-only; קובץ אחד לכל (task_id) מספיק כי run מזוהה בכל שורה."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_step(self, record: StepRecord) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def write_summary(self, summary: RunSummary) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"summary": True, **asdict(summary)}, ensure_ascii=False) + "\n")


@dataclass(frozen=True)
class SafetyNets:
    """שלוש רשתות הביטחון של Task 3. חריגה היא outcome מתועד (terminal_state=cap_breached),
    לעולם לא קריסה או קיטוע שקט."""

    max_iterations: int = 12
    token_budget: int = 30_000
    timeout_s: float = 90.0

    def breach(self, steps: int, tokens_used: int, elapsed_s: float) -> str | None:
        if steps >= self.max_iterations:
            return "max_iterations"
        if tokens_used >= self.token_budget:
            return "token_budget"
        if elapsed_s >= self.timeout_s:
            return "timeout"
        return None
