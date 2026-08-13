# IMPLEMENTATION.md

טבלה חיה — מתעדכנת תוך כדי ביצוע כל artifact, לא בלילה לפני הגשה (M13).

| ID | Concept | Tier | Where | Why |
|----|---------|------|-------|-----|
| M1 | CLAUDE.md — constitution | Must | `CLAUDE.md` | הפרויקט כבר צבר החלטות שקל לשחזר לא נכון (למשל: alias לא מתוארך למודל Gemini אחרי ש-`gemini-2.0-flash` קרס ב-404; הרצה בודדת בלבד מול המודל המקומי) — CLAUDE.md מונע חזרה על אותן טעויות בסשן הבא. |
| M2 | שני rules, שני scopes | Must | `.claude/rules/hosted-llm-quota.md` (always-on), `.claude/rules/tax-data-sourcing.md` (path-scoped ל-`data/**/*.md`) | ה-throttling ל-Gemini הוא constraint גורף לכל סקריפט (always-on); דרישת sourcing למספרי מס רלוונטית רק לקבצי `data/*.md` — לכן שני scopes נפרדים, לא כלל כללי מדי אחד. |
| M3 | Skill — add-llm-script | Must | `.claude/skills/add-llm-script/SKILL.md` | הדפוס (client setup, utf-8 stdout, קילוף JSON fence) כבר חזר 3 פעמים בקוד (`hello_llm.py`, `file_qa.py`, `qa_experiment.py`) בלי שהיה מתועד במקום אחד — סיכון ממשי שסקריפט רביעי ישכפל טעות (למשל ישכח את ה-encoding fix) במקום לעקוב אחרי הדפוס שכבר עבד. |
| M4 | Subagent — groundedness-reviewer | Must | `.claude/agents/groundedness-reviewer.md` | tools מוגבל בכוונה ל-`Read, Grep, Glob` (בלי Edit/Write/Bash) כדי שסקירת hallucination תישאר read-only — לא רוצים שסוכן שתפקידו לבקר יוכל בטעות "לתקן" את `data/tax_notes.md` תוך כדי ביקורת. |

## Skipped, and why
(יתעדכן בהמשך — Session 1 עוסק רק ב-M1–M4.)

## What I'd do differently next time
(יתעדכן בסיום כל הסשנים.)
