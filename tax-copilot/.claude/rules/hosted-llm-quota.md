---
description: Throttle and retry sequential Gemini calls to respect the free-tier rate limit
---

Gemini free tier מוגבל ל-15 req/min. כל סקריפט שמבצע כמה קריאות ברצף ל-Gemini (hosted) חייב:

- throttle בין קריאות (`time.sleep`) — לא loop חופשי בלי המתנה.
- retry עם backoff על `RateLimitError`.

בדיוק הדפוס שכבר קיים ב-`qa_experiment.py`: `time.sleep(4)` בין קריאות, ועד 5 ניסיונות עם `sleep(15)` ב-retry.

אם מוסיפים סקריפט חדש עם loop של קריאות ל-Gemini בלי throttling — לעצור ולתקן לפני שמריצים.

**עדכון (assignment3):** ב-`src/llm.py` ההגבלה נאכפת כעת **בתוך** `call_text` (`_wait_for_slot`, רצפה של 4.2 שניות בין קריאות), ולא באחריות הקורא. `llm.throttle()` נשאר כ-no-op לתאימות. סקריפט חדש שמשתמש ב-`src/llm.py` מקבל את הקצב הנכון בחינם.

## CODIFY log
- **2026-08-13** — נתקלנו בתקרה נפרדת ולא-מתועדת מראש: מודלים non-lite (`gemini-flash-latest`, `gemini-3.5-flash` וכו') מוגבלים ל-**20 בקשות/יום** בלבד ב-free tier (בניגוד ל-15 req/**דקה** של מודלי `-lite`) — נשרפה התקרה פעמיים תוך כדי בחירת judge model ל-assignment2. נימוק: 15 req/min חל רק על טייר lite; טייר רגיל חסום כמעט לחלוטין ב-free tier. תיקון: לכל צורך ב"מודל שונה" (bias reduction וכו') לבחור checkpoint אחר **בטייר lite** (למשל `gemini-3.1-flash-lite`) במקום לעבור לטייר non-lite.
