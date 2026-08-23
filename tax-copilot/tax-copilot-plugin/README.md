# tax-copilot-toolkit (X5)

Packages this project's own `.claude/` artifacts into one installable, versioned unit: the `/mark-checklist-item` command, the `add-llm-script` skill, the `groundedness-reviewer` agent, and both hooks (`block_env_leak.py`, `audit_log.py`).

**This is a packaging exercise, not the source of truth.** The live `.claude/` at the project root is what Claude Code actually loads day to day and is what M2–M11 in `IMPLEMENTATION.md` document; this directory is a copy, and the two will drift unless kept in sync by hand. That tradeoff — a real, explained cost, not a hidden one — is the point of doing X5 as a genuine second copy instead of a symlink or an empty demo manifest with no content behind it.

One functional difference from the project original: `audit_log.py` here writes its `audit.jsonl` next to itself inside the installed plugin, not into this project's `.claude/hooks/`, since a redistributed plugin has no project-specific log path to write to.
