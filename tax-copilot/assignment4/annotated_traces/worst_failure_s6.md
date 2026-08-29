# Annotated trace #2 — Worst failure

**Task:** `s6` (single), run 1, config=agent, model=gemini-flash-lite-latest
**Question:** "שכירה עם משכורת 18,000 ₪ (אישה) תורמת 5,000 ₪ בשנה. מה גובה זיכוי המס השנתי שלה מהתרומה?"
**success_criteria:** `answer contains "1750.00" or "1750" (±1)`
**Result:** success=bad, terminal_state=refused

This is the single worst-performing task in the whole Task 5 matrix: **1/5 success** across
all 5 runs (4× refused/cap_breached, 1× answered correctly), versus 5/5 on every other
`single` task. This trace is the pre-fix behavior that grounds the Task 6 experiment
(see `assignment4_writeup.md`, Task 6, experiment 1).

## Step-by-step

**Step 1 — `search_tax_corpus`** (query: `"תרומה זיכוי 46"`)
→ retrieved 5 chunks: disability/dependent-care credit caps (§44/45), a links list, a
secondary-sources list, self-employed-guide sources, and a general credit-point table.
**None of the 5 chunks contain the section 46 donation-credit rate or formula.**

**❌ Annotation — where it went wrong (1/3):** one of the retrieved chunks (page 7 of
`income-tax-deductions-booklet-2026`) *does* mention the existence of the mechanism —
"6. הקמת מערכת 'תרומות ישראל' ומתן זיכוי לפי סעיף46 לפקודת מס הכנסה" — but only names
it, with no percentage or formula. The corpus was never meant to carry a computable
donation-credit rate for arbitrary donation/salary combinations; that's exactly what
`calculate_tax_refund`'s `annual_donation` parameter exists for. The retrieval isn't
"wrong" here so much as *structurally the wrong tool for this sub-question*.

**Step 2 — `search_tax_corpus`** (query: `"תרומות סעיף 46"`)
→ retrieved 5 chunks again: real-estate tax law references, retirement-age tables,
the same page-7 mention as step 1, an unrelated deductions table, and the credit-point
table again.

**❌ Annotation — where it went wrong (2/3):** a second corpus search with a narrower
query still can't produce a number, because there is no number to retrieve — this is a
computation, not a lookup. The agent doesn't yet recognize "two corpus misses on a
credit/refund question" as the trigger to fall back to `calculate_tax_refund`, which was
available the entire time and never called in this run.

**Step 3 — final answer (no tool call):**
> "לא מצאתי את זה במסמכים או בכלים הזמינים." *(I didn't find this in the documents or
> available tools.)*

**❌ Annotation — where it went wrong (3/3, the actual failure):** this is the system
prompt's rule 4 firing ("if the answer isn't in any available tool — not the corpus, not
computable — refuse"). The model's own text explicitly claims the tools were checked
("או בכלים הזמינים"), but `calculate_tax_refund` — the one tool that *can* answer this in
one call, given the salary and donation amount already stated in the question — was never
invoked. The agent conflated "the corpus doesn't have it" with "it isn't computable."

## Contrast: the one run that succeeded (run 2)

Run 2 of the same task went straight to `search_tax_corpus` once, then correctly pivoted
to `calculate_tax_refund(gross_salary=18000, gender="female", annual_donation=5000)` and
returned the exact right figure (1,750.00 ₪, §46 credit). Same task, same tools, same
model — the only difference is whether the model happened to try the second tool before
giving up. That 1-in-5 split (not 0-in-5 or 5-in-5) is exactly the "reading a rate, not a
boolean" warning from the assignment: this is a real reliability gap in tool selection,
not a one-off fluke.

## Fix applied (Task 6, experiment 1)

`calculate_tax_refund`'s docstring was rewritten to explicitly state up front that it is
the correct tool for *any* salary + credit/refund question — including donations — and
that a failed corpus search on a credit question means "try this tool," not "refuse."
See `assignment4_writeup.md` for the measured before/after on this exact task.
