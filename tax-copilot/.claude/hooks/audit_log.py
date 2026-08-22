"""PostToolUse hook: appends one JSONL audit entry per Write/Edit call.

Never blocks — always exits 0, even if logging itself fails, so a broken
audit trail can't stop real work.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent / "audit.jsonl"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        tool_name = payload.get("tool_name", "")
        file_path = (payload.get("tool_input", {}) or {}).get("file_path", "")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": file_path,
            "tool": tool_name,
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
