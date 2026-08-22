"""S5 headless run: checks src/tax_refund_calculator.py's hardcoded tax
constants against their source, data/tax_notes.md, via `claude -p
--output-format json`.

Why this exists (see CLAUDE.md Open questions): the calculator hardcodes
tax brackets, National Insurance rates, and credit-point values as Python
constants instead of reading tax_notes.md at runtime. .claude/rules/
tax-data-sourcing.md only covers data/**/*.md, not .py files, so nothing
catches the two drifting silently if tax_notes.md is ever updated for a
new tax year. This script is that missing check, run on demand (or from
CI) instead of never.

Exit 0: constants match the doc. Exit 1: a mismatch was found (or Claude
couldn't produce parseable JSON) -- either way, a human should look.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
CALCULATOR = REPO_ROOT / "src" / "tax_refund_calculator.py"
SOURCE_DOC = REPO_ROOT / "data" / "tax_notes.md"

PROMPT = f"""Compare the hardcoded tax constants in {CALCULATOR.name} against
their documented source in {SOURCE_DOC.name}. Both files are in this
repo -- read them yourself with Read.

{CALCULATOR.name} defines these constant groups, each with a "מקור:
tax_notes.md §N" comment marking which section of {SOURCE_DOC.name} it
was taken from: TAX_BRACKETS, CREDIT_POINT_VALUE_MONTHLY,
BASE_CREDIT_POINTS, NI_REDUCED_THRESHOLD, NI_CEILING, NI_RATE_LOW,
NI_RATE_HIGH, HEALTH_RATE_LOW, HEALTH_RATE_HIGH,
KEREN_HISHTALMUT_DEDUCTIBLE_CAP_MONTHLY, DONATION_CREDIT_RATE,
DONATION_MIN_ANNUAL.

For each one, check whether the value in the code still matches the
number given in the cited section of {SOURCE_DOC.name}.

Respond with ONLY a JSON object, no prose, no markdown fence:
{{"in_sync": true|false, "mismatches": [{{"constant": "...",
"code_value": "...", "doc_value": "..."}}]}}

"mismatches" is an empty list when everything matches.
"""


def _strip_code_fence(text: str) -> str:
    """Gemini/Claude sometimes wrap JSON in a ```/```json fence even when
    asked not to -- same convention as llm.py's fence-stripping."""
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text


def main() -> int:
    result = subprocess.run(
        [
            "claude", "-p", PROMPT,
            "--output-format", "json",
            "--allowedTools", "Read",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        print(f"claude -p failed (exit {result.returncode}): {result.stderr}", file=sys.stderr)
        return 1

    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"could not parse claude -p envelope: {exc}", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        return 1

    print(f"cost: ${envelope.get('total_cost_usd', '?')} | turns: {envelope.get('num_turns', '?')}")

    try:
        payload = json.loads(_strip_code_fence(envelope["result"]))
    except (KeyError, json.JSONDecodeError) as exc:
        print(f"could not parse drift-check result JSON: {exc}", file=sys.stderr)
        print(envelope.get("result", ""), file=sys.stderr)
        return 1

    if payload.get("in_sync"):
        print("in sync: all constants match data/tax_notes.md")
        return 0

    print("DRIFT DETECTED:")
    for m in payload.get("mismatches", []):
        print(f"  {m.get('constant')}: code={m.get('code_value')!r} doc={m.get('doc_value')!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
