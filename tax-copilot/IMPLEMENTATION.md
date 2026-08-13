# IMPLEMENTATION.md

טבלה חיה — מתעדכנת תוך כדי ביצוע כל artifact, לא בלילה לפני הגשה (M13).

| ID | Concept | Tier | Where | Why |
|----|---------|------|-------|-----|
| M1 | CLAUDE.md — constitution | Must | `CLAUDE.md` | הפרויקט כבר צבר החלטות שקל לשחזר לא נכון (למשל: alias לא מתוארך למודל Gemini אחרי ש-`gemini-2.0-flash` קרס ב-404; הרצה בודדת בלבד מול המודל המקומי) — CLAUDE.md מונע חזרה על אותן טעויות בסשן הבא. |
| M2 | שני rules, שני scopes | Must | `.claude/rules/hosted-llm-quota.md` (always-on), `.claude/rules/tax-data-sourcing.md` (path-scoped ל-`data/**/*.md`) | ה-throttling ל-Gemini הוא constraint גורף לכל סקריפט (always-on); דרישת sourcing למספרי מס רלוונטית רק לקבצי `data/*.md` — לכן שני scopes נפרדים, לא כלל כללי מדי אחד. |
| M3 | Skill — add-llm-script | Must | `.claude/skills/add-llm-script/SKILL.md` | הדפוס (client setup, utf-8 stdout, קילוף JSON fence) כבר חזר 3 פעמים בקוד (`hello_llm.py`, `file_qa.py`, `qa_experiment.py`) בלי שהיה מתועד במקום אחד — סיכון ממשי שסקריפט רביעי ישכפל טעות (למשל ישכח את ה-encoding fix) במקום לעקוב אחרי הדפוס שכבר עבד. |
| M4 | Subagent — groundedness-reviewer | Must | `.claude/agents/groundedness-reviewer.md` | tools מוגבל בכוונה ל-`Read, Grep, Glob` (בלי Edit/Write/Bash) כדי שסקירת hallucination תישאר read-only — לא רוצים שסוכן שתפקידו לבקר יוכל בטעות "לתקן" את `data/tax_notes.md` תוך כדי ביקורת. |
| M5 | Spec-first feature — מחשבון מס והחזר לשכיר | Must | `specs/tax-refund-calculator.md` (commit `e32fee4`) → `src/tax_refund_calculator.py` (commit `f548f4c`) | ה-spec נכתב ונכנס ל-git **לפני** שורת קוד אחת של המימוש (שני commits נפרדים, לפי הסדר) — כדי לתפוס אי-התאמות (למשל תבנית EARS "Optional feature" מול "Complex") לפני שהן מתקבעות בקוד. 5 קריטריוני EARS + out-of-scope מפורש + test vectors שנשלפו מדוגמאות מחושבות שכבר קיימות ומצוטטות ב-`data/tax_notes.md` (לא sourcing חדש), ואומתו בפועל מול המימוש — 4/4 עברו. |
| M6 | CODIFY log — 4 כשלים אמיתיים מתועדים | Must | סעיף `## CODIFY log` ב-`CLAUDE.md` (3 entries) + `.claude/rules/hosted-llm-quota.md` (1 entry) | כל entry מתועד כי שינה התנהגות בפועל: `gemini-2.0-flash` קרס ב-404 (מודל מתוארך), cp1255 קרס על עברית ב-Windows, Gemini עטף JSON ב-fence, ומודלים non-lite נתקלים בתקרת 20 req/יום (לא 15/min כמו lite). פוצל בין CLAUDE.md ל-rules כי ה-checklist מפרש "CLAUDE.md **+** rules" (רבים) — לא קובץ יחיד. |

## Skipped, and why
(יתעדכן בהמשך — Session 1–2 מכסים M1–M6.)

## What I'd do differently next time
(יתעדכן בסיום כל הסשנים.)
