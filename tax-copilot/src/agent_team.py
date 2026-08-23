"""X4: a real multi-provider agent team, run from Python instead of the
Claude Code Agent tool -- the distinction the checklist actually asked for
("teammates" vs. a subagent inside the same session).

Workers audit the same thing X3's corpus-sourcing-audit.js workflow does
(TaxData/ sourcing, per .claude/agents/groundedness-reviewer.md), but each is
a direct LLM API call instead of a Claude Code subagent. Workers run on
Gemini (already wired in llm.py, free-tier lite model) so the fan-out costs
nothing; the lead-merge step is the one deliberate Anthropic API call per
run, on claude-haiku-4-5 -- kept to a single call so "Anthropic API directly"
stays true without N-times the paid cost.
"""

import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import truststore
from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

from llm import GENERATOR_MODEL as GEMINI_MODEL
from llm import call_structured

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

# This machine's network path injects a self-signed root CA (corporate
# proxy/AV TLS inspection) that the OS trusts but Python's bundled certifi
# does not -- openai's plain httpx client fails TLS verification against it,
# while anthropic's SDK (whose httpx2 fork already uses the OS trust store)
# does not. Patching ssl to use the OS store here fixes the Gemini worker
# calls too, without disabling verification. Scoped to this module only, not
# to llm.py, so it doesn't change behavior for any other script.
truststore.inject_into_ssl()

SRC_DIR = Path(__file__).resolve().parent
REPO_ROOT = SRC_DIR.parent.parent  # src/ -> tax-copilot/ -> repo root (TaxData/ lives here)
MANIFEST_PATH = SRC_DIR.parent / "assignment3" / "data" / "corpus_manifest.json"

LEAD_MODEL = "claude-haiku-4-5"

# $ per 1M tokens. Gemini lite models are free-tier (see CLAUDE.md Cost
# discipline), so only the Anthropic side needs a real rate.
ANTHROPIC_PRICING = {"claude-haiku-4-5": {"input": 1.0, "output": 5.0}}

# Gemini's own pacing (llm._wait_for_slot) is a bare global-variable
# check-then-set with no lock -- correct for the sequential callers it was
# written for, but a race under ThreadPoolExecutor: several worker threads
# could all read the same _last_call_at before any of them updates it, and
# fire close together instead of MIN_SECONDS_BETWEEN_CALLS apart, which is
# exactly the burst .claude/rules/hosted-llm-quota.md exists to prevent.
# Serializing worker calls through this lock makes the pacing correct again;
# the workers still fan out and read their document in parallel, only the
# LLM call itself is single-file.
_gemini_call_lock = threading.Lock()

_anthropic_client: Anthropic | None = None


def get_anthropic_client() -> Anthropic:
    """Lazy, same reason as llm.get_client(): building at import time would
    crash any import of this module (e.g. under pytest) when
    ANTHROPIC_API_KEY is unset."""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _anthropic_client


@dataclass(frozen=True)
class ProviderUsage:
    provider: str  # "gemini" | "anthropic"
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float

    @property
    def cost_usd(self) -> float:
        if self.provider == "gemini":
            return 0.0
        rates = ANTHROPIC_PRICING[self.model]
        return (self.input_tokens * rates["input"] + self.output_tokens * rates["output"]) / 1_000_000


class UnsourcedFigure(BaseModel):
    figure: str
    location: str


class WorkerReport(BaseModel):
    doc_name: str
    unsourced_figures: list[UnsourcedFigure]


@dataclass(frozen=True)
class WorkerResult:
    doc_name: str
    report: WorkerReport | None
    usage: ProviderUsage | None
    error: str | None = None


@dataclass(frozen=True)
class TeamRunResult:
    worker_results: list[WorkerResult]
    report_markdown: str
    lead_usage: ProviderUsage


WORKER_SYSTEM_PROMPT = """אתה מבקר groundedness בלבד, לצוות ביקורת אוטומטי. אתה קורא מסמך מס אחד ומדווח, ואינך משנה קבצים.

עבור על המסמך שסופק וזהה כל מספר, אחוז, או סף (threshold) הקשור למס שמופיע בלי ציטוט/הפניה למקור רשמי.
המסמך נמצא מחוץ ל-tax-copilot/, ולכן אין sourcing rule אוטומטי שחל עליו -- התייחס לכל מספר כאילו הוא זקוק למקור.

החזר אך ורק JSON תקני, ללא code fences וללא טקסט נוסף, בפורמט:
{"doc_name": "<שם המסמך>", "unsourced_figures": [{"figure": "...", "location": "..."}]}
אם לא נמצאו -- unsourced_figures צריך להיות רשימה ריקה."""

LEAD_SYSTEM_PROMPT = """את/ה מרכז/ת צוות ביקורת מסמכי מס. קיבלת דוחות JSON נפרדים, אחד לכל מסמך, שכל אחד \
דיווח על מספרים ללא מקור. מזג אותם לדוח Markdown יחיד ותמציתי: כותרת עם מספר כולל של ממצאים ופירוט לפי מסמך \
(כמה ממצאים בכל מסמך), ואז לכל מסמך שיש בו ממצאים -- עד 10 דוגמאות מייצגות בלבד (לא רשימה ממצה של כולם), \
עם ציון "ועוד N נוספים" אם יש יותר. בעברית. אל תמציא ממצאים שלא הופיעו בקלט."""


def load_manifest() -> list[dict]:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def _read_document_text(doc: dict) -> str:
    """Markdown files are read as text; the PDF is extracted the same way
    build_index.py already does for RAG indexing (PyPDFLoader), so this
    doesn't invent a second PDF-reading path."""
    abs_path = REPO_ROOT / doc["path"]
    if doc["format"] == "pdf":
        from langchain_community.document_loaders import PyPDFLoader
        pages = PyPDFLoader(str(abs_path)).load()
        return "\n\n".join(p.page_content for p in pages)
    return abs_path.read_text(encoding="utf-8")


def _audit_document(doc: dict) -> WorkerResult:
    try:
        text = _read_document_text(doc)
    except Exception as e:  # noqa: BLE001 -- a bad path/file shouldn't crash the whole team run
        return WorkerResult(doc_name=doc["doc_name"], report=None, usage=None, error=str(e))

    user_content = f"doc_name: {doc['doc_name']}\n\n{text}"
    try:
        with _gemini_call_lock:
            parsed, raw = call_structured(WORKER_SYSTEM_PROMPT, user_content, WorkerReport)
    except Exception as e:  # noqa: BLE001 -- surfaced to the lead as a per-doc failure, not a crash
        return WorkerResult(doc_name=doc["doc_name"], report=None, usage=None, error=str(e))

    usage = ProviderUsage(provider="gemini", model=GEMINI_MODEL, input_tokens=raw.input_tokens,
                           output_tokens=raw.output_tokens, latency_ms=raw.latency_ms)
    return WorkerResult(doc_name=doc["doc_name"], report=parsed, usage=usage)


def run_workers(manifest: list[dict]) -> list[WorkerResult]:
    """One worker per document, dispatched in parallel; the Gemini call
    itself is serialized (see _gemini_call_lock)."""
    with ThreadPoolExecutor(max_workers=len(manifest)) as pool:
        return list(pool.map(_audit_document, manifest))


def merge_reports(worker_results: list[WorkerResult]) -> tuple[str, ProviderUsage]:
    """The one Anthropic API call per team run."""
    payload = [
        {"doc_name": r.doc_name, "unsourced_figures": [f.model_dump() for f in r.report.unsourced_figures]}
        for r in worker_results if r.report is not None
    ]
    failed = [r.doc_name for r in worker_results if r.report is None]
    user_content = json.dumps(payload, ensure_ascii=False)
    if failed:
        user_content += f"\n\nמסמכים שנכשלו בביקורת ולא נכללים למעלה: {', '.join(failed)}"

    response = get_anthropic_client().messages.create(
        model=LEAD_MODEL,
        # 2000 truncated a real run mid-sentence once six documents' worth of
        # findings (285 rows in one measured run) came back from the workers;
        # each row is short, so 8192 covers a full corpus run with headroom.
        max_tokens=8192,
        system=LEAD_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    usage = ProviderUsage(provider="anthropic", model=LEAD_MODEL, input_tokens=response.usage.input_tokens,
                           output_tokens=response.usage.output_tokens, latency_ms=0.0)
    return text, usage


def run_team(manifest: list[dict] | None = None) -> TeamRunResult:
    manifest = manifest if manifest is not None else load_manifest()
    worker_results = run_workers(manifest)
    report_markdown, lead_usage = merge_reports(worker_results)
    return TeamRunResult(worker_results=worker_results, report_markdown=report_markdown, lead_usage=lead_usage)


if __name__ == "__main__":
    result = run_team()
    print(result.report_markdown)
    total_cost = sum(r.usage.cost_usd for r in result.worker_results if r.usage) + result.lead_usage.cost_usd
    print(f"\n---\nעלות כוללת: ${total_cost:.4f} "
          f"(Gemini workers: $0, Anthropic lead: ${result.lead_usage.cost_usd:.4f})")
