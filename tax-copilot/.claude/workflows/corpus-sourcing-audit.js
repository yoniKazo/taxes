/**
 * X3: Dynamic Workflow — audit every TaxData/ corpus document for sourcing,
 * the way .claude/rules/tax-data-sourcing.md audits data/**\/*.md.
 *
 * Why this exists: tax-data-sourcing.md is path-scoped to `data/**\/*.md`,
 * and rules don't cross the project-directory boundary -- so it never
 * reaches TaxData/, which sits one level up (repo root, sibling of
 * tax-copilot/) and holds tax figures for four more domains than the
 * calculator's employees-only scope. That gap is already documented in
 * CLAUDE.md's Open questions and "What I'd do differently." This workflow
 * is the mechanical answer: it can't reach further than the rule can, but
 * it can be run on demand against a real list -- the corpus manifest.
 *
 * Default is pipeline(); this uses parallel() because the six documents
 * are genuinely independent (no fact in one depends on another), and the
 * merge step genuinely needs every result at once -- the one place a
 * barrier is correct here.
 *
 * `agentType` selects an existing .claude/agents/<name>.md subagent by
 * name -- documented consistently across third-party Claude Code guides,
 * but not confirmed against an official Anthropic reference page as of
 * writing. Verify via /workflows -> "View raw script" (or by asking
 * Claude Code to regenerate this file) against your installed version
 * before depending on this in an unattended run.
 */

export const meta = {
  name: 'corpus-sourcing-audit',
  description: 'Audit every TaxData/ corpus document for unsourced tax figures',
}

const manifest = await agent(
  'Read assignment3/data/corpus_manifest.json (relative to the repo root, ' +
  'one level above the current project directory) and return its contents.',
  {
    schema: {
      type: 'object',
      required: ['documents'],
      properties: {
        documents: {
          type: 'array',
          items: {
            type: 'object',
            required: ['doc_name', 'path'],
            properties: {
              doc_name: { type: 'string' },
              path: { type: 'string' },
            },
          },
        },
      },
    },
  },
)

const reviews = await parallel(
  manifest.documents.map((doc) => () =>
    agent(
      `Review the document at ${doc.path} (repo-root-relative path) for ` +
      'unsourced tax figures: any number, percentage, or threshold stated ' +
      'without a citation to an official source. This document is outside ' +
      'tax-copilot/, so .claude/rules/tax-data-sourcing.md does not apply ' +
      'to it automatically -- treat every figure as needing a source.',
      {
        agentType: 'groundedness-reviewer',
        label: doc.doc_name,
        schema: {
          type: 'object',
          required: ['doc_name', 'unsourced_figures'],
          properties: {
            doc_name: { type: 'string' },
            unsourced_figures: {
              type: 'array',
              items: {
                type: 'object',
                required: ['figure', 'location'],
                properties: {
                  figure: { type: 'string' },
                  location: { type: 'string' },
                },
              },
            },
          },
        },
      },
    ),
  ),
)

const report = await agent(
  'Merge these per-document sourcing audits into one report, grouped by ' +
  'document, with a total unsourced-figure count at the top:\n' +
  JSON.stringify(reviews.filter(Boolean)),
  { label: 'merge-report' },
)

return report
