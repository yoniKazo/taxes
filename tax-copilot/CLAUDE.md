# CLAUDE.md — tax-copilot

## Forbidden
- לחשוף/להדפיס ערכי API keys, או לקומיט `.env` (רק `.env.example` עם ערך ריק נכנס לגיט).
- להמציא או לשנות מספרי מס ב-`data/tax_notes.md` בלי מקור ברשימת המקורות בתחתית הקובץ.
- להריץ את מטריצת ה-27 השילובים של `qa_experiment.py` מול המודל המקומי (`bloomz-560m`) — הוא רץ **פעם אחת בלבד** כרפרנס, כי כל קריאה מקומית לוקחת דקות על CPU (הסיבה מתועדת ב-`experiment_results.md`).
- לקבע שם מודל Gemini מתוארך (למשל `gemini-2.0-flash`) — שמות כאלה כבר קרסו ב-404; להשתמש רק ב-alias לא מתוארך כמו `gemini-flash-lite-latest`.

## Conventions
- עברית לפרומפטים/תיעוד/הודעות; אנגלית למזהי קוד (functions, variables).
- כל סקריפט חדש שקורא ל-LLM מתארח עוקב אחרי הדפוס הקיים ב-`hello_llm.py`/`file_qa.py`/`qa_experiment.py` (ראו `.claude/skills/add-llm-script/`).
- `sys.stdout.reconfigure(encoding="utf-8")` בתחילת כל סקריפט שמדפיס עברית (אחרת קריסה על cp1255 בווינדוס).
- קילוף ```` ``` ```` code fences לפני `json.loads`/`pydantic` — Gemini לפעמים עוטף JSON ב-markdown fence גם כשמתבקש "JSON בלבד".
- Type hints על חתימות פונקציות; ללא docstrings ארוכות — שורה אחת רק כשלא ברור מהשם.

## Stack & architecture
- Python + `.venv` (`requirements.txt`: openai, pydantic, python-dotenv, transformers, torch).
- ספק מתארח: Gemini, דרך `openai` SDK מול endpoint תואם-OpenAI (`base_url=".../v1beta/openai/"`) — לא SDK ילידי, כי לא הייתה גישה לקונסולת Anthropic.
- `pydantic` ל-validation של structured output (`hello_llm.py`).
- מודל מקומי: `bigscience/bloomz-560m` דרך `transformers.pipeline`, בלי API key (`local_llm.py`).
- `python-dotenv` טוען `GEMINI_API_KEY` מ-`.env` (בgitignore).
- אין עדיין vector store/chunking — `file_qa.py` מזין את `data/tax_notes.md` במלואו לקונטקסט (single-doc grounding, לא RAG אמיתי).

## Command cheatsheet
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src\hello_llm.py
python src\file_qa.py data\tax_notes.md "שאלה"
python src\local_llm.py
python src\qa_experiment.py
```

## Open questions
- אין retrieval אמיתי — כש-`data/tax_notes.md` יגדל מעבר לחלון ההקשר, יידרש chunking/embeddings.
- אין remote/CI (local-only). S6 (Claude Code ב-CI) חסום עד שיוחלט על git remote.
- איכות המודל המקומי חלשה (`bloomz-560m`, נבחר כי כבר מותקן, לא לאיכות) — לשקול מחדש לפני שימוש user-facing.
- Scope נוכחי: שכירים בלבד. הרחבה לעצמאים היא החלטה עתידית, לא ברירת מחדל.
