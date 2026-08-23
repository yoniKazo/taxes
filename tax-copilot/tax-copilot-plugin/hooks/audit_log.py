"""PostToolUse hook: appends one JSONL audit entry per file-affecting call.

Never blocks — always exits 0, even if logging itself fails, so a broken
audit trail can't stop real work.

Write/Edit always log. Bash only logs when the command contains a
write-signal token (heuristic, not proof — see CLAUDE.md note); this
keeps read-only noise like `git status`/`ls` out of the trail while still
catching `python ...`, `> file`, `tee`, `mv`, `cp`, `rm`, which this
project uses to touch files outside the Write/Edit tools.

This log is git-tracked by design (M10), so the logged command text is
redacted before storage: `NAME=value` inline env-var assignments (the
exact shape this project has used for `GEMINI_API_KEY=... python ...`)
are stripped to `NAME=***` before truncation, so a secret typed inline
on the command line can't end up committed and pushed via the audit
trail itself (security-review finding, 2026-08-23).
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent / "audit.jsonl"

_BASH_WRITE_SIGNAL_RE = re.compile(
    r"(^|\s)(python3?|mv|cp|rm|tee)\b|>>?|\btee\b"
)

_INLINE_ENV_ASSIGNMENT_RE = re.compile(r"\b([A-Z_][A-Z0-9_]*)=(\S+)")


def _redact(command: str) -> str:
    return _INLINE_ENV_ASSIGNMENT_RE.sub(r"\1=***", command)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        tool_name = payload.get("tool_name", "")
        tool_input = payload.get("tool_input", {}) or {}

        if tool_name == "Bash":
            command = tool_input.get("command", "") or ""
            if not _BASH_WRITE_SIGNAL_RE.search(command):
                return 0
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": None,
                "tool": tool_name,
                "command": _redact(command)[:200],
            }
        else:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": tool_input.get("file_path", ""),
                "tool": tool_name,
            }

        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
