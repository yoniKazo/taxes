---
description: מסמן פריט מה-27-checklist כהושלם — הופך checkbox ל-[x] ב-HomeWork/agentic-infra-tasks.md ומוסיף/מעדכן שורה תואמת בטבלה של IMPLEMENTATION.md (ID/Concept/Tier/Where/Why), על בסיס git log/diff אחרונים. Use when a checklist item (M#/S#/X#) was just implemented and both tracking files need updating, instead of hand-editing both every time.
argument-hint: [item-id]
---

# סימון פריט checklist כהושלם: $ARGUMENTS

פריט: `$ARGUMENTS` (מזהה בפורמט M/S/X + מספר, לדוגמה `M7`).

1. בדוק את ה-commits/diff האחרונים (`git log --oneline -15`, ובמידת הצורך `git show`) כדי להבין מה בפועל מומש עבור `$ARGUMENTS`.
2. ב-`HomeWork/agentic-infra-tasks.md`: מצא את השורה עם `**$ARGUMENTS**` והחלף `- [ ]` ל-`- [x]`. אם כבר מסומן — אל תיגע.
3. ב-`IMPLEMENTATION.md`: אם כבר יש שורה ל-`$ARGUMENTS` עדכן אותה; אחרת הוסף שורה חדשה (סדר ID עולה). Tier נגזר מהקידומת (M=Must, S=Should, X=Stretch). עמודת Why חייבת להיות נימוק אמיתי וספציפי — לא ניסוח מחדש של הדרישה מה-checklist.
4. הצג את ה-diff הסופי של שני הקבצים ועצור. **אל תעשה git commit** — זו החלטה נפרדת של המשתמש.
