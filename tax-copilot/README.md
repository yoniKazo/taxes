# Tax Copilot

פרויקט לקורס AI/LLM Engineering. הנושא (theme) שנבחר לכל הקורס: ייעוץ מס וחיסכון במס לשכיר ולעצמאי — ריפו זה יגדל בהדרגה עם כל מטלה.

תוצרי כל מטלה יושבים בתיקייה נפרדת עם שם תואם (`assignment1/`, `assignment2/`, ...). `data/` בשורש הוא בסיס ידע משותף שממשיך לשמש מטלות עתידיות. כל הפקודות למטה מריצות מתוך שורש `tax-copilot/`.

## מטלה 1 — Your First LLM App

- `assignment1/hello_llm.py` — קריאה ל-LLM מתארח דרך ה-OpenAI-compatible endpoint: קריאה בסיסית, system prompt, temperature, פלט JSON מובנה.
- `assignment1/file_qa.py` — Q&A ממוסמך יחיד (`data/tax_notes.md`), עונה רק לפי המסמך ומצטט קטע תומך.
- `assignment1/local_llm.py` — הרצת מודל פתוח מקומי (`bigscience/bloomz-560m`) ללא API key.
- `assignment1/reflections.md` — תשובות לשאלות ההרהור.

**ספק ה-LLM המתארח:** Gemini (Google AI Studio), דרך ה-endpoint התואם-OpenAI שלו — הוחלף מ-Claude כי לא הייתה גישה לקונסולת Anthropic. אותו קוד בדיוק, רק `base_url`/`api_key`/`model` שונים — בדיוק הנקודה שהמטלה מבקשת להמחיש.

## סטאפ

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

הגדרת מפתח API (ל-`hello_llm.py` ו-`file_qa.py` בלבד — `local_llm.py` לא צריך מפתח). מפתח Gemini מתקבל ב-[aistudio.google.com](https://aistudio.google.com) → Get API key.

המפתח נשמר מקומית בקובץ `.env` (לא נכנס לגיט — כלול ב-`.gitignore`) ונטען אוטומטית ב-`load_dotenv()`. פשוט פתחו את `.env` והדביקו את המפתח:

```
GEMINI_API_KEY=AIza...
```

## הרצה

```powershell
python assignment1\hello_llm.py
python assignment1\file_qa.py data\tax_notes.md "האם עצמאי חייב במקדמות מס?"
python assignment1\local_llm.py
python assignment1\qa_experiment.py
```
