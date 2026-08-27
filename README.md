---
title: Tax Copilot
emoji: 🧾
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Taxes

Monorepo root (`github.com/yoniKazo/taxes.git`). **`tax-copilot/` is the project root for the "Agentic Engineering" course, Part 2** — the 27-artifact submission described below lives there, not here.

## Why the split

- `tax-copilot/` — the course project itself (code, `.claude/`, specs, docs).
- `TaxData/` — a shared tax-reference corpus used by `tax-copilot/`'s RAG pipeline (assignment 3), kept as a sibling because it's a general-purpose data source, not an asset of one assignment.
- `.github/workflows/` — must sit here, at the repo root, because GitHub Actions only scans `.github/` at the top level; each workflow uses `working-directory: tax-copilot` to run against the project.
- `HomeWork/` — course material and tracking docs (gitignored; not part of the deliverable).

## 27-artifact map

Source: `HomeWork/project-requirements-checklist.md` (13 Must, 7 Should, 7 Stretch). Deliverable: [`tax-copilot/IMPLEMENTATION.md`](tax-copilot/IMPLEMENTATION.md).

| ID | Concept | Path |
|----|---------|------|
| M1 | CLAUDE.md constitution | [`tax-copilot/CLAUDE.md`](tax-copilot/CLAUDE.md) |
| M2 | Two rules, two scopes | [`tax-copilot/.claude/rules/`](tax-copilot/.claude/rules/) |
| M3 | Skill | [`tax-copilot/.claude/skills/add-llm-script/`](tax-copilot/.claude/skills/add-llm-script/) |
| M4 | Subagent | [`tax-copilot/.claude/agents/groundedness-reviewer.md`](tax-copilot/.claude/agents/groundedness-reviewer.md) |
| M5 | Spec-first feature | [`tax-copilot/specs/tax-refund-calculator.md`](tax-copilot/specs/tax-refund-calculator.md) |
| M6 | CODIFY log | [`tax-copilot/CLAUDE.md`](tax-copilot/CLAUDE.md) (§ CODIFY log) + [`tax-copilot/.claude/rules/hosted-llm-quota.md`](tax-copilot/.claude/rules/hosted-llm-quota.md) |
| M7 | Slash command | [`tax-copilot/.claude/commands/mark-checklist-item.md`](tax-copilot/.claude/commands/mark-checklist-item.md) |
| M8 | MCP decision | [`tax-copilot/IMPLEMENTATION.md`](tax-copilot/IMPLEMENTATION.md) |
| M9 | PreToolUse blocking hook | [`tax-copilot/.claude/hooks/block_env_leak.py`](tax-copilot/.claude/hooks/block_env_leak.py) |
| M10 | PostToolUse audit hook | [`tax-copilot/.claude/hooks/audit_log.py`](tax-copilot/.claude/hooks/audit_log.py) |
| M11 | Permissions policy | [`tax-copilot/.claude/settings.json`](tax-copilot/.claude/settings.json) |
| M12 | Agent Responsibility Contract | `tax-copilot/contract.md` |
| M13 | IMPLEMENTATION.md | [`tax-copilot/IMPLEMENTATION.md`](tax-copilot/IMPLEMENTATION.md) |
| S1 | Plan Mode, largest change | `tax-copilot/plans/` |
| S2 | Nested CLAUDE.md | `tax-copilot/api/CLAUDE.md` |
| S3 | /code-review before PR | `tax-copilot/reviews/` |
| S4 | /security-review | `tax-copilot/reviews/` |
| S5 | Headless run | `tax-copilot/scripts/` |
| S6 | Claude Code in CI | `.github/workflows/claude.yml` (repo root) |
| S7 | Cost discipline | [`tax-copilot/IMPLEMENTATION.md`](tax-copilot/IMPLEMENTATION.md) |
| X1 | Custom MCP server | `tax-copilot/mcp_servers/` |
| X2 | Spec Kit run | `tax-copilot/specs/` |
| X3 | Dynamic Workflow | `tax-copilot/.claude/workflows/` |
| X4 | Agent Team run | `tax-copilot/IMPLEMENTATION.md` |
| X5 | Plugin | `tax-copilot/tax-copilot-plugin/` |
| X6 | Background run | `tax-copilot/IMPLEMENTATION.md` |
| X7 | Codebase knowledge graph | `tax-copilot/graphify-out/` |

See [`tax-copilot/README.md`](tax-copilot/README.md) for how to run the app.
