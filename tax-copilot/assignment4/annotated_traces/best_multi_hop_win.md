# Annotated trace #1 — Best multi-hop win

**Task:** `mh1` (multi_hop), run 1, config=agent, model=gemini-flash-lite-latest
**Question:** "כמה מס רכישה אשלם על דירה שנייה (לא דירה יחידה) בשווי 4,000,000 ₪?"
**success_criteria:** `answer contains "320,000" or "320000" (±1)`
**Result:** success=good, terminal_state=answered, tool_calls=2, tools_used=[search_tax_corpus, calculator]

This is a genuine multi-hop: the tax **rate** (8%, for a second/non-single home under
the current in-force bracket) only exists in the RAG corpus; the **arithmetic**
(4,000,000 × 8%) is not in any document and must be computed. Neither tool alone
answers the question — this is exactly the shape Task 3's tool set was designed to force.

## Step-by-step

**Step 1 — `search_tax_corpus`** (query: `"מס רכישה דירה שנייה מדרגות שווי 4,000,000"`)
→ retrieved `real-estate-tax-guide`, including the exact table:

> ### 3.2 דירת מגורים נוספת (שאינה דירה יחידה, הוראת שעה — סעיף 9(ג1ו) לחוק)
> בתוקף מיום 16.1.2025 ועד יום 31.12.2026:
>
> | חלק השווי (₪) | שיעור מס |
> |---|---|
> | עד 6,055,070 | 8% (מהשקל הראשון) |
> | מעל 6,055,070 | 10% |

**✅ Annotation — where it went right (1/2):** the agent's query already includes the
exact shekel figure from the question (not just "מס רכישה דירה שנייה"), which is why
the single retrieval call surfaced the *correct* bracket (second-home, not single-home
or non-residential) out of five very similar-looking tables in the same document chunk.
A weaker query here (as seen in other runs of this same task, see below) still recovers
the right table, but this phrasing got it on the first and only search — no wasted call.

**Step 2 — `calculator`** (expression: `"0.08 * 4000000"`) → `320000`

**✅ Annotation — where it went right (2/2):** the model correctly identified that
4,000,000 ₪ falls entirely under the first bracket (≤ 6,055,070 ₪ → flat 8% from the
first shekel, no marginal-rate blending needed), and handed the *exact* arithmetic
expression to `calculator` instead of computing "in its head" — this is the intended
division of labor (tool retrieves facts, tool computes, model never does either itself).

**Step 3 — final answer:**
> על פי מדרגות מס הרכישה לדירת מגורים נוספת (שאינה דירה יחידה), עבור שווי של עד
> 6,055,070 ₪ חל שיעור מס של **8%** מהשקל הראשון.
>
> לפיכך, עבור דירה בשווי 4,000,000 ₪ תשלם מס רכישה בסך **320,000 ₪** (שהם 8% מתוך
> 4,000,000 ₪).

Correct, cited to the retrieved bracket, and states the applicable date range from the
source — good grounding, not just a bare number.

## Why this run, not another mh1 run

Other recorded runs of this exact task (visible in the same raw trace file, from earlier
attempts before checkpointing existed) needed a *second*, broader search query
(`"מס רכישה דירה שנייה שיעור"`) before landing on the same table — same final answer,
one extra tool call. This run is the cleanest 2-call version and is representative of
mh1's 5/5 success rate across the full Task 5 matrix.
