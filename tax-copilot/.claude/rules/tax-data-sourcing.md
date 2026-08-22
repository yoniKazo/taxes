---
description: Every tax figure added to data/*.md must be sourced and scoped to employees only
paths:
  - "data/**/*.md"
---

- כל מספר/עובדת מס שנוספת או משתנה חייבת מקור ברשימת המקורות בתחתית הקובץ (ראו סוף `data/tax_notes.md`).
- Scope נוכחי: שכירים (שכיר) בלבד — לא עצמאים. זו החלטת scope מפורשת, לא מקרית.
- הרחבה לעצמאים או הוספת מספר בלי מקור מחייבת אישור מפורש מהמשתמש לפני עריכה.

**מה הכלל הזה לא מכסה (assignment3):** קורפוס ה-RAG יושב ב-`TaxData/` שברמת הריפו, מחוץ ל-`tax-copilot/`, ולכן מחוץ ל-`paths` של הכלל הזה. הוא גם רחב ממנו ב-scope — יש בו עצמאים, מקרקעין ושוק ההון. הסטנדרט שם מתועד ב-`TaxData/README.md` (ציטוט מקור רשמי לכל נתון, רמות אמינות, פערים ידועים) ונאכף ידנית. שינוי ב-`TaxData/` מחייב גם `python src\build_index.py` מחדש.
