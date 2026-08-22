"""Background jobs for the operations that take minutes.

Two callers need this. Rebuilding an index re-embeds every chunk on CPU, and a
test run fires one throttled LLM call per question -- both are minutes of work
behind a request that currently returns nothing until it finishes, so the UI can
only show a disabled button.

Deliberately in-memory: this is a single-user local app with no worker process
and no queue. Jobs do not survive a restart, and uvicorn --reload restarts on
every file save. That is an accepted limit, not an oversight.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

# One worker on purpose. Embedding saturates the CPU, and two concurrent index
# builds would make both slower than running them in sequence.
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="job")

_LOCK = threading.Lock()
_JOBS: dict[str, "Job"] = {}

# Finished jobs are kept so a poll that arrives after completion still gets the
# result; the cap stops a long session from growing without bound.
MAX_RETAINED = 50


@dataclass
class Job:
    id: str
    kind: str
    status: str = "pending"  # pending | running | done | error | cancelled
    phase: str = ""
    done: int = 0
    total: int = 0
    result: Any = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    _cancelled: bool = False

    def to_dict(self) -> dict:
        return {
            "job_id": self.id,
            "kind": self.kind,
            "status": self.status,
            "phase": self.phase,
            "done": self.done,
            "total": self.total,
            "progress": round(self.done / self.total, 3) if self.total else None,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
        }


Reporter = Callable[[str, int, int], None]


def submit(kind: str, fn: Callable[[Reporter, Callable[[], bool]], Any]) -> Job:
    """`fn(report, should_cancel)` runs on the worker thread.

    It should call report(phase, done, total) as it progresses and check
    should_cancel() between items -- cancellation is cooperative because there
    is no safe way to kill a thread mid-embedding.
    """
    job = Job(id=uuid.uuid4().hex[:12], kind=kind)
    with _LOCK:
        _prune_locked()
        _JOBS[job.id] = job

    def report(phase: str, done: int, total: int) -> None:
        job.phase, job.done, job.total = phase, done, total

    def run() -> None:
        job.status = "running"
        try:
            job.result = fn(report, lambda: job._cancelled)
            job.status = "cancelled" if job._cancelled else "done"
        except Exception as exc:  # noqa: BLE001 -- surfaced to the client verbatim
            job.status = "cancelled" if job._cancelled else "error"
            job.error = str(exc)

    _EXECUTOR.submit(run)
    return job


def get(job_id: str) -> Job | None:
    return _JOBS.get(job_id)


def cancel(job_id: str) -> Job | None:
    job = _JOBS.get(job_id)
    if job and job.status in {"pending", "running"}:
        job._cancelled = True
    return job


def _prune_locked() -> None:
    finished = [j for j in _JOBS.values() if j.status in {"done", "error", "cancelled"}]
    if len(_JOBS) <= MAX_RETAINED:
        return
    for job in sorted(finished, key=lambda j: j.created_at)[: len(_JOBS) - MAX_RETAINED]:
        _JOBS.pop(job.id, None)
