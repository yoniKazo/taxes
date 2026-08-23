# /security-review — 2026-08-23, branch diff (`agentic-infra-completion` vs `master`)

**S4.** Run on the full branch diff (26 commits, every M12/S1–S7/X1–X7 artifact added). Scope: new code only, per the review's own instructions — MCP server, headless script, CI workflow, hook changes, dynamic workflow, plugin.

## Findings

### 1. Secret exfiltration via audit log — `tax-copilot/.claude/hooks/audit_log.py`

* **Severity**: High
* **Category**: sensitive data exposure
* **Description**: The M10 fix in this branch (commit `67c06f4`) extended the audit hook's `PostToolUse` matcher from `Write|Edit` to `Write|Edit|Bash`, capturing raw Bash command text into `audit.jsonl` — a file intentionally git-tracked (M10's whole point is a queryable, committed history). Any command containing an inline `KEY=value` assignment (e.g. `GEMINI_API_KEY="..." python hello_llm.py` — a pattern this exact project's own `.claude/settings.local.json` permission history already recorded once) matched the write-signal regex and got the full secret persisted verbatim into a file headed for `git commit` / `git push`, neither of which is blocked (both are `ask`-tier, not `deny`).
* **Exploit scenario**: A developer runs a command with an inline API key (as this project's history shows already happened). The hook silently logs it. A later `git add .claude/hooks/audit.jsonl && git commit && git push` — an entirely ordinary, unblocked action — puts the live key into pushed git history, readable by anyone with repo access.
* **Outcome**: **Fixed** in this same review, same commit. `_redact()` strips any `NAME=value` inline env-var assignment to `NAME=***` before truncation/storage, closing the path while preserving the audit trail's value (which command ran, not its secret payload). Verified live: a piped test command containing a fake key was correctly redacted before being written to `audit.jsonl`. The identical fix was synced into `tax-copilot-plugin/hooks/audit_log.py` (X5's packaged copy of the same hook), which had the same flaw.

## Not flagged (reviewed and excluded)

- **`.github/workflows/claude.yml`**: `github.event.comment.body` is read only inside an `if:` expression (`contains(...)`), never interpolated into a `run:` shell block — no script-injection path exists (the classic `${{ }}`-inside-`run:` pattern is absent here).
- **`mcp_servers/tax_corpus.py`**: inputs come from the trusted local Claude Code session's own tool calls, not external/untrusted callers; no path traversal (chunk lookup is structural metadata matching, not filesystem path construction from input).
- **`scripts/tax_constants_drift.py`**: `subprocess.run` called with an argument list (not `shell=True`), and the prompt is a static f-string with no untrusted interpolation — no command injection surface.
- **`.claude/workflows/corpus-sourcing-audit.js`**: prompts passed to `agent()` are LLM prompt content, not shell/SQL/code execution — prompt-injection-into-an-LLM-prompt is out of scope per this review's own exclusions.
- Vendored Spec Kit installer scripts (`.specify/scripts/powershell/*.ps1`) — third-party, not authored in this branch; out of scope.

**One finding, fixed, none rejected.**
