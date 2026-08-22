---
name: add-llm-script
description: Use when adding a new Python script in tax-copilot that calls the hosted Gemini LLM via the OpenAI-compatible client (keywords - Gemini, hosted LLM, openai client, new script, base_url). Ensures the script follows the project's established connection/encoding/parsing pattern instead of re-deriving it from scratch.
---

# הוספת סקריפט חדש שקורא ל-Gemini

Procedure חוזרת (כבר בשימוש ב-`hello_llm.py`, `file_qa.py`, `qa_experiment.py`) — לפני כתיבת סקריפט חדש שמדבר עם Gemini דרך ה-endpoint התואם-OpenAI:

1. **Client setup** — להעתיק את דפוס ה-client הקיים:
   ```python
   from dotenv import load_dotenv
   from openai import OpenAI

   load_dotenv()
   client = OpenAI(
       base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
       api_key=os.environ["GEMINI_API_KEY"],
   )
   MODEL = "gemini-flash-lite-latest"  # alias, לא שם מתוארך
   ```
2. **Encoding** — `sys.stdout.reconfigure(encoding="utf-8")` בתחילת הקובץ, לפני כל הדפסה — אחרת קריסה על עברית בcp1255 בווינדוס.
3. **אם מצפים לפלט JSON** — לקלף code fence לפני parsing (Gemini לפעמים עוטף ```` ```json ... ``` ````):
   ```python
   if raw.startswith("```"):
       raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
   ```
4. **קריאות מרובות ברצף** — לכבד את מגבלת free-tier (15 req/min): throttle + retry על `RateLimitError` (ראו `.claude/rules/hosted-llm-quota.md` ואת הדפוס ב-`qa_experiment.py`).
5. **מפתח** — לעולם לא הדפסה/קומיט של `GEMINI_API_KEY`; רק קריאה מ-`.env` דרך `os.environ`.
