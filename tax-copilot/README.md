# Tax Copilot

פרויקט לקורס AI/LLM Engineering. הנושא (theme) שנבחר לכל הקורס: ייעוץ מס וחיסכון במס — ריפו זה יגדל בהדרגה עם כל מטלה. **Scope נוכחי: שכירים בלבד** (ראו `CLAUDE.md`) — הרחבה לעצמאים היא החלטה עתידית, לא ברירת מחדל.

כל הקוד יושב ב-`src/` (לא מחולק לפי מטלה). תוצרי כל מטלה (תוצאות ריצה, כתיבות, נתונים) יושבים בתיקייה נפרדת עם שם תואם (`assignment1/`, `assignment2/`, ...). `data/` בשורש הוא בסיס ידע משותף שממשיך לשמש מטלות עתידיות. כל הפקודות למטה מריצות מתוך שורש `tax-copilot/`.

## מטלה 1 — Your First LLM App

- `src/hello_llm.py` — קריאה ל-LLM מתארח דרך ה-OpenAI-compatible endpoint: קריאה בסיסית, system prompt, temperature, פלט JSON מובנה.
- `src/file_qa.py` — Q&A ממוסמך יחיד (`data/tax_notes.md`), עונה רק לפי המסמך ומצטט קטע תומך.
- `src/local_llm.py` — הרצת מודל פתוח מקומי (`bigscience/bloomz-560m`) ללא API key.
- `assignment1/reflections.md` — תשובות לשאלות ההרהור.

**ספק ה-LLM המתארח:** Gemini (Google AI Studio), דרך ה-endpoint התואם-OpenAI שלו — הוחלף מ-Claude כי לא הייתה גישה לקונסולת Anthropic. אותו קוד בדיוק, רק `base_url`/`api_key`/`model` שונים — בדיוק הנקודה שהמטלה מבקשת להמחיש.

## מטלה 2 — Evaluation-Driven Development

grounded Q&A bot על `data/tax_notes.md`, עם רוברייק כתובה מראש, מחזור שיפור מבוסס-ממצאים, ו-LLM-as-judge מול הערכה אנושית.

- `assignment2/assignment2_rubric.md` — Task 1: הרוברייק (6 קריטריונים — Fluency/Grammar/Tone/Length/Grounding/Latency, pass bar, go/no-go rules), נכתבה **לפני** כל הרצה.
- `assignment2/data/tax_qa_dataset.md` — 24 שאלות ב-3 קטגוריות (יש-במסמך / לא-קיים-כלל / מתחכמת).
- `src/assignment2_generate.py` — Task 2: יוצר תשובה לכל 24 השאלות מול Gemini (`gemini-flash-lite-latest`), מודד `latency_ms`/tokens בקוד. פלט: `assignment2/assignment_02.xlsx`.
- Task 3 — הערכה ידנית (baseline) על מדגם של 14 שורות: **14/14 pass**, אפס `bad`. הכשל היחיד שחזר: בולרפלייט פתיחה/סגירה שפגע ב-Tone.
- `src/assignment2_experiments.py` — Task 4: שני ניסויים על אותן 14 שורות — (1) איסור מפורש בפרומפט על ברכות/תארים שיווקיים → **תיקן את Tone ל-14/14 good**; (2) `temperature=0` בלבד, ללא שינוי פרומפט → **לא עזר** (אף החמיר מעט), מוכיח שהבעיה הייתה תלוית-פרומפט. פלט: `assignment2/assignment2_experiments.xlsx`.
- `src/assignment2_judge.py` — Task 5+6: LLM-as-judge (`gemini-3.1-flash-lite`, checkpoint שונה מהיצירה כדי לצמצם self-enhancement bias) שופט את כל 24 השורות; Latency מדורג תכנותית מ-`latency_ms`, לא נשלח ל-judge. תוצאה: **24/24 pass**; הסכמה מלאה (100%) עם האדם על 5/6 קריטריונים, ו-71% על Tone — פער שמאתר עמימות אמיתית ברוברייק, לא טעות של אף צד.
- `assignment2/assignment2_writeup.md` — הכתיבה המלאה: ניתוח agreement, trade-offs (עלות/קנה-מידה/עקביות/דיוק), והמלצת production (judge בשער הראשי + human-in-the-loop מדגמי, עם go/no-go קשיח בקוד על Grounding).

## מחשבון מס והחזר לשכיר

`src/tax_refund_calculator.py` — כלי דטרמיניסטי (ללא LLM): מקבל שכר ברוטו חודשי + נקודות זיכוי, ומחזיר מס הכנסה, ביטוח לאומי/בריאות ונטו, כולל חיסכון מס אופציונלי מהפרשת פנסיה/קרן השתלמות ומזיכוי תרומה (סעיף 46). זו התכונה הראשונה שבאמת "מחשבת" ולא רק עונה על שאלות — נבנתה spec-first: `specs/tax-refund-calculator.md` (EARS + out-of-scope) לפני קוד.

## נתונים (`data/`)

- `data/tax_notes.md` — הבסיס למס שכיר 2026: מדרגות, נקודות זיכוי, ביטוח לאומי/בריאות, פנסיה, קרן השתלמות, סעיף 46, ודוגמאות מחושבות. כל מספר מגובה במקור (ראו `.claude/rules/tax-data-sourcing.md`).
- `data/tax_law_history.md` — הבסיס החוקי (סעיפי פקודת מס הכנסה) וציר זמן של שינויי חקיקה רלוונטיים לשכיר מ-2003 ואילך.

## תשתית Agentic Engineering

לצד המטלות הממוספרות, הריפו הזה בונה בהדרגה שכבת `.claude/` (CLAUDE.md, rules, skills, agents, specs, hooks) לפי checklist נפרד. מצב מלא ומנומק — כולל מה דולג ולמה — ב-`IMPLEMENTATION.md`.

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
python src\hello_llm.py
python src\file_qa.py data\tax_notes.md "האם עצמאי חייב במקדמות מס?"
python src\local_llm.py
python src\qa_experiment.py

python src\assignment2_generate.py
python src\assignment2_experiments.py
python src\assignment2_judge.py --sanity
python src\assignment2_judge.py

python src\tax_refund_calculator.py 13000 male --pension-pct 0.06 --keren-hishtalmut 500 --donation 2000
```
