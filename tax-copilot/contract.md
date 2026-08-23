# Agent Responsibility Contract

What Claude Code can do in this repo without asking, what needs your explicit yes, and what it must never do — and what happens when things go wrong repeatedly. This mirrors `.claude/settings.json`'s `permissions` block and `.claude/hooks/block_env_leak.py` exactly; if this file and those don't agree, the mechanical layer (settings.json + hook) wins, and this file is out of date.

## CAN without approval

- Read, search, and list any file (`Read`, `Grep`, `Glob`).
- Run Python scripts and pytest (`Bash(python *)`, `Bash(pytest*)`).
- Read git history and state (`git status`, `git diff`, `git log`, `git show`) — never write git operations.

## REQUIRES explicit approval

- Editing or creating any file (`Edit`, `Write`).
- `git commit`, `git push`.
- `pip install`.

These change something that persists after the session ends — the working tree, git history, or the Python environment — so a human confirms each one.

## FORBIDDEN

- Reading or printing the contents of `.env`, in any form (`cat`/`type`/`more`/`less`/`Get-Content .env`, or a direct `Read`/`Edit`/`Write` on it). `.env.example` is explicitly exempt.
- Staging or committing `.env` to git (`git add .env*`, including `git add -f`).
- `rm -rf` with any arguments.
- Writing or editing anything under `assignment3/index/` — this is the canonical FAISS index every assignment-3 script loads; a write here silently forks the index from the source data it's supposed to represent. (UI-built custom indexes go to `assignment3/index_custom/`, which is unrestricted.)

Every rule above has a mechanical twin: the `.env` rules are enforced by both `.claude/hooks/block_env_leak.py` (which inspects the actual command/file text and exits 2) and the `deny` list in `.claude/settings.json` (which blocks by permission pattern before the tool even runs); `rm -rf*` and the `assignment3/index/**` writes are `deny`-only. A FORBIDDEN line with no matching `deny` entry or hook check is not a real rule — it's a sentence a model might not read twice.

**Not in this list on purpose:** "never swap the measurement instrument (judge model, metric, judge prompt) mid-experiment," which is Forbidden #5 in `CLAUDE.md`. There's no mechanical way to detect "this edit changes a judge's behavior" versus any other code edit, so it stays a convention enforced by review, not a rule enforced by a hook. Listing it here would fail this document's own consistency test.

## Escalation rule

Stop and report instead of retrying when either happens:

- **3 failed tool calls in a row on the same task.** Don't try a 4th variation — describe what was attempted and what failed, and wait for direction.
- **A `RateLimitError` repeats twice.** The Gemini free-tier quota (15 req/min on `-lite` models, 20 req/**day** on non-lite — see `.claude/rules/hosted-llm-quota.md`) is a hard external ceiling, not something a longer sleep fixes. The daily 500-call budget has already been exhausted once mid-run ([phaseb_run.log](assignment3/data/phaseb_run.log)) by not stopping here.
