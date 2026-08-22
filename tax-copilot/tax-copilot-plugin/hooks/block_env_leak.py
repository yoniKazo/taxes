"""PreToolUse hook: blocks exposing/committing .env (CLAUDE.md Forbidden #1).

Reads a single tool-call JSON object from stdin. Exits 2 (block) with a
reason on stderr if the call would read .env's contents, write/overwrite
.env, or stage/commit it to git. .env.example is always allowed.
"""
import json
import re
import sys

_ENV_TOKEN = r"\.env\b(?!\.example)"

ENV_READ_RE = re.compile(
    r"\b(cat|type|more|less|Get-Content|gc)\b[^\n]*" + _ENV_TOKEN
)
ENV_GIT_STAGE_RE = re.compile(r"\bgit\s+add\b[^\n]*" + _ENV_TOKEN)
ENV_GIT_COMMIT_RE = re.compile(r"\bgit\s+commit\b[^\n]*" + _ENV_TOKEN)


def is_env_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    name = normalized.rsplit("/", 1)[-1]
    return name == ".env"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}

    if tool_name == "Bash":
        command = tool_input.get("command", "") or ""
        if ENV_READ_RE.search(command):
            print("blocked: command reads .env contents", file=sys.stderr)
            return 2
        if ENV_GIT_STAGE_RE.search(command) or ENV_GIT_COMMIT_RE.search(command):
            print("blocked: command stages/commits .env to git", file=sys.stderr)
            return 2

    if tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path", "") or ""
        if is_env_path(file_path):
            print("blocked: direct write/edit of .env", file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
