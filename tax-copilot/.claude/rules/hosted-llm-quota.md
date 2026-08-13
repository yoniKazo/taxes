---
description: Throttle and retry sequential Gemini calls to respect the free-tier rate limit
---

Gemini free tier מוגבל ל-15 req/min. כל סקריפט שמבצע כמה קריאות ברצף ל-Gemini (hosted) חייב:

- throttle בין קריאות (`time.sleep`) — לא loop חופשי בלי המתנה.
- retry עם backoff על `RateLimitError`.

בדיוק הדפוס שכבר קיים ב-`qa_experiment.py`: `time.sleep(4)` בין קריאות, ועד 5 ניסיונות עם `sleep(15)` ב-retry.

אם מוסיפים סקריפט חדש עם loop של קריאות ל-Gemini בלי throttling — לעצור ולתקן לפני שמריצים.
