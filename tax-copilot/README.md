# Tax Copilot

פרויקט לקורס AI/LLM Engineering. הנושא (theme) שנבחר לכל הקורס: ייעוץ מס וחיסכון במס — ריפו זה יגדל בהדרגה עם כל מטלה. **Scope נוכחי: שכירים בלבד** (ראו `CLAUDE.md`) — הרחבה לעצמאים היא החלטה עתידית, לא ברירת מחדל.

כל הקוד יושב ב-`src/` (לא מחולק לפי מטלה). תוצרי כל מטלה (תוצאות ריצה, כתיבות, נתונים) יושבים בתיקייה נפרדת עם שם תואם (`assignment1/`, `assignment2/`, ...). `data/` בשורש הוא בסיס ידע משותף שממשיך לשמש מטלות עתידיות. קורפוס ה-RAG של מטלה 3 יושב **מחוץ** ל-`tax-copilot/` — ב-`TaxData/` שברמת הריפו (`../TaxData`), כי הוא מאגר המס הכללי של הפרויקט ולא נכס של מטלה בודדת; הנתיבים הרשומים ב-`assignment3/data/corpus_manifest.json` הם יחסית לשורש הריפו. כל הפקודות למטה מריצות מתוך שורש `tax-copilot/`.

## מטלה 1 — Your First LLM App

- `src/hello_llm.py` — קריאה ל-LLM מתארח דרך ה-OpenAI-compatible endpoint: קריאה בסיסית, system prompt, temperature, פלט JSON מובנה.
- `src/file_qa.py` — Q&A ממוסמך יחיד (`data/tax_notes.md`), עונה רק לפי המסמך ומצטט קטע תומך.
- `src/local_llm.py` — הרצת מודל פתוח מקומי (`bigscience/bloomz-560m`) ללא API key.
- `assignment1/reflections.md` — תשובות לשאלות ההרהור.

> ה-Q&A המבוסס-מקור (`file_qa.py`) ניתן להרצה גם דרך קליינט הדפדפן (agent בשם `qa`, במסך "בדיקות AI") ולא רק כסקריפט CLI — ראו [קליינט דפדפן](#קליינט-דפדפן-react-fastapi) למטה.

**ספק ה-LLM המתארח:** Gemini (Google AI Studio), דרך ה-endpoint התואם-OpenAI שלו — הוחלף מ-Claude כי לא הייתה גישה לקונסולת Anthropic. אותו קוד בדיוק, רק `base_url`/`api_key`/`model` שונים — בדיוק הנקודה שהמטלה מבקשת להמחיש.

## מטלה 2 — Evaluation-Driven Development

grounded Q&A bot על `data/tax_notes.md`, עם רוברייק כתובה מראש, מחזור שיפור מבוסס-ממצאים, ו-LLM-as-judge מול הערכה אנושית.

> **כל מחזור ההערכה הזה — רוברייק, דאטהסט, יצירה, ניקוד אנושי, judge והשוואת agreement — ניתן להרצה גם דרך קליינט הדפדפן** (מסך "בדיקות AI"), לא רק דרך הסקריפטים וה-`.xlsx` שמתוארים כאן. הרוברייק והדאטהסט למטה הם בדיוק מה שנטען אוטומטית ל-SQLite עם עליית ה-API (`seed_if_empty`) — זו אותה רוברייק, לא גרסה מקבילה. ראו [קליינט דפדפן](#קליינט-דפדפן-react-fastapi).

- `assignment2/assignment2_rubric.md` — Task 1: הרוברייק (6 קריטריונים — Fluency/Grammar/Tone/Length/Grounding/Latency, pass bar, go/no-go rules), נכתבה **לפני** כל הרצה.
- `assignment2/data/tax_qa_dataset.md` — 24 שאלות ב-3 קטגוריות (יש-במסמך / לא-קיים-כלל / מתחכמת).
- `src/assignment2_generate.py` — Task 2: יוצר תשובה לכל 24 השאלות מול Gemini (`gemini-flash-lite-latest`), מודד `latency_ms`/tokens בקוד. פלט: `assignment2/assignment_02.xlsx`.
- Task 3 — הערכה ידנית (baseline) על מדגם של 14 שורות: **14/14 pass**, אפס `bad`. הכשל היחיד שחזר: בולרפלייט פתיחה/סגירה שפגע ב-Tone.
- `src/assignment2_experiments.py` — Task 4: שני ניסויים על אותן 14 שורות — (1) איסור מפורש בפרומפט על ברכות/תארים שיווקיים → **תיקן את Tone ל-14/14 good**; (2) `temperature=0` בלבד, ללא שינוי פרומפט → **לא עזר** (אף החמיר מעט), מוכיח שהבעיה הייתה תלוית-פרומפט. פלט: `assignment2/assignment2_experiments.xlsx`.
- `src/assignment2_judge.py` — Task 5+6: LLM-as-judge (`gemini-3.1-flash-lite`, checkpoint שונה מהיצירה כדי לצמצם self-enhancement bias) שופט את כל 24 השורות; Latency מדורג תכנותית מ-`latency_ms`, לא נשלח ל-judge. תוצאה: **24/24 pass**; הסכמה מלאה (100%) עם האדם על 5/6 קריטריונים, ו-71% על Tone — פער שמאתר עמימות אמיתית ברוברייק, לא טעות של אף צד.
- `assignment2/assignment2_writeup.md` — הכתיבה המלאה: ניתוח agreement, trade-offs (עלות/קנה-מידה/עקביות/דיוק), והמלצת production (judge בשער הראשי + human-in-the-loop מדגמי, עם go/no-go קשיח בקוד על Grounding).

## מטלה 3 — RAG על קורפוס מיסוי ישראלי

צינור RAG מלא (FAISS + embeddings מקומיים) מעל שישה מסמכי מס אמיתיים ב-`TaxData/`, מוערך מול בייסליין ללא-RAG על אותן 34 שאלות.

> **גם כל המטלה הזו ניתנת להרצה מהדפדפן** — מסך "מעבדת RAG" (`/rag`) מכסה את שבע המשימות, כולל בניית אינדקס ומדידת hit@k בלי לשרוף ולו קריאת LLM אחת. ראו [קליינט דפדפן](#קליינט-דפדפן-react-fastapi).

- **הקורפוס** — 6 מסמכים, 2 פורמטים, 151 צ'אנקים (`RecursiveCharacterTextSplitter`, 1000/150): חמשת מדריכי ה-md של `TaxData/` + "לוח עזר לחישוב מס הכנסה ממשכורת, ינואר 2026" של רשות המסים (PDF, 32 עמ'). יש כאן **חפיפה מכוונת בין מקור למשני** — חלק ממדריכי ה-md נגזרו מאותו PDF — וזה מה שמייצר שאלות multi-hop אמיתיות. האינדקס הקנוני `assignment3/index/` הוא **לקריאה בלבד**.
- **מודל embedding: `intfloat/multilingual-e5-small`, לא `BAAI/bge-small-en-v1.5` שהמטלה קיבעה.** סטייה מנומקת ונמדדת, לא נוחות: על קורפוס עברי bge נותן hit@5 של 0.719 מול 0.969. bge נשמר ונמדד שוב כניסוי מתועד ב-Task 6.
- `src/build_index.py` — parse → chunk → enrich → embed → store (Task 1/3); הרצה ישירה מדפיסה 10 צ'אנקים אקראיים ו-3 שאילתות בדיקה — צעד ה"actually look at it" שהמטלה דורשת. `src/embeddings.py` — prefix conventions, שונים לכל מודל embedding. `src/rag_pipeline.py` — אחזור, תשובה מעוגנת עם ציטוטי `[n]`, ומשמר ציטוטים דטרמיניסטי שפוסל הפניה מחוץ לטווח. `src/retrieval_eval.py` — hit@k. `src/judges.py` — ארבעת השופטים (context relevance, faithfulness, answer relevance, correctness).
- **מערך ההערכה** (`assignment3/data/tax_rag_eval_set.csv`) — 34 שאלות: 28 סינתטיות (`easy`, נוצרו מצ'אנק בודד לכל קריאה, כך שהמסמך/סעיף של אותו צ'אנק הוא תווית ה-ground truth של האחזור — בחינם) + 6 בכתב יד (`hard`: 2 multi-hop, 2 unanswerable, 1 negation, 1 exact-identifier).
- **Task 5 — התוצאה המרכזית**: RAG מכפיל את ה-correctness פי 2.1 (**0.765** מול **0.368** לבייסליין) ומוריד סירובים שגויים מ-18 ל-3. המחיר: latency פי 3.4 ו-input tokens פי 16. אפס false answers בשתי המערכות; hit-rate@5 ברמת מסמך = 0.969.
- **הפער בין הפרוסות הוא הסיפור, לא הממוצע** — בפרוסה הקלה hit@k ו-faithfulness שניהם 1.000; בקשה הם 0.750 ו-0.333. מספר ממוצע יחיד היה מסתיר את זה לגמרי. (6 שאלות בפרוסה הקשה = ~16.7 נקודות אחוז לשאלה — הדלתאות שם מדווחות ככיוון, לא כהוכחה.)
- `src/assignment3_experiments.py` — Task 6: 12 קונפיגורציות (top-K, chunk size, embedding, hybrid BM25) נסרקו **ב-0 קריאות API**, כי hit-rate הוא בוליאני לשאלה ולא דורש שופט. המסקנות: k=8 מנקה את הפרוסה הקשה (0.750 → 1.000) בלי לפגוע בקלה, chunk size 1000/150 כבר באופטימום, ו-BM25 היברידי לא מנצח dense טהור באף משקל — כלומר ההשערה שנרשמה מראש הופרכה עוד לפני שהוצא תקציב שופטים.
- `assignment3/assignment3_writeup.md` — הכתיבה המלאה: שלוש הסטיות המוצהרות מהמטלה, נזקי ה-parsing ב-PDF, ניתוח (א)/(ב)/(ג), ושני ממצאים שנוגעים למכשירי המדידה עצמם — באג ground-truth במערך ההערכה (שאלת unanswerable שתויגה אחרי grep ב-md בלבד, בעוד התשובה הייתה ב-PDF), וכשל כיול ב-`judge_faithfulness` שנבנה בלי לראות את השאלה ולכן דירג **סירובים נכונים** כ-`bad`. השופט תוקן בקוד אך במכוון **לא** הוחל רטרואקטיבית באמצע ניסוי; המכשיר נמדד בנפרד ב-`src/assignment3_judge_recalibration.py`.

> **סטטוס פתוח:** Task 6 שלב ב' הורץ **חלקית**, ומתועד ככזה. `exp1` (`top_k=8`) — יצירה מלאה, שיפוט על 6/34 שורות (הפרוסה הקשה); `exp2` (bge) — יצירה מלאה, **ללא שיפוט**; `exp3` (hybrid BM25) — לא רץ. העצירה: מכסת 500 הקריאות היומית של Gemini (`assignment3/data/phaseb_run.log`). מה שכן הוסק — hit@k, שיעורי סירוב, latency וטוקנים — חושב מקבצי היצירה השמורים ב-**0 קריאות**, ומספיק כדי להכריע את exp2 לבדו: bge מפיל את המערכת ל-20 סירובים שגויים מתוך 32 לעומת 3. שתי אזהרות כיול מתועדות ב-writeup, כולל שהקפיצה ב-faithfulness בין Task 5 ל-exp1 היא **החלפת מכשיר ולא אפקט של k**.

## מחשבון מס והחזר לשכיר

`src/tax_refund_calculator.py` — כלי דטרמיניסטי (ללא LLM): מקבל שכר ברוטו חודשי + נקודות זיכוי, ומחזיר מס הכנסה, ביטוח לאומי/בריאות ונטו, כולל חיסכון מס אופציונלי מהפרשת פנסיה/קרן השתלמות ומזיכוי תרומה (סעיף 46). זו התכונה הראשונה שבאמת "מחשבת" ולא רק עונה על שאלות — נבנתה spec-first: `specs/tax-refund-calculator.md` (EARS + out-of-scope) לפני קוד.

## קליינט דפדפן (React + FastAPI)

מעל הכלים והסקריפטים שמתוארים למעלה יש עכשיו גם אפליקציית web מלאה — לא תחליף למטלות הממוספרות, אלא דרך נוספת (ויזואלית, אינטראקטיבית) להריץ את אותה עבודה ממש:

- **`api/`** — שרת FastAPI. `POST /calculate` מפעיל את `tax_refund_calculator.calculate_multi_job` (כמה עבודות בו-זמנית, תיאום מס אמיתי — ראו `specs/tax-refund-calculator-multi-job.md`) ואת agent ה-`explainer` להסבר בעברית פשוטה. שאר ה-endpoints מפעילים את שכבת ה-Test Lab (ראו מטה). כל קריאת LLM — מהמחשבון וגם מה-Test Lab — נרשמת ב-SQLite (`api/data/tax_copilot.db`, לא נכנס לגיט): השאלה, איזה agent, איזה מודל/טמפרטורה, התשובה, ומיונים אם ניתנו.
- **מסך "מחשבון"** — הזנת כמה עבודות + נקודות זיכוי/פנסיה/קרן השתלמות/תרומות, מקבלים מס+נטו מחושבים, ו"הסבר" בעברית פשוטה מ-agent ה-`explainer`.
- **מסך "בדיקות AI"** — הגרסה האינטראקטיבית של מטלה 2 (ראו שם למעלה): רוברייק ניתנת לצפייה ועריכה (עריכה יוצרת גרסה חדשה, לא דורסת ישנה), רשימת 24 השאלות ניתנת לצפייה/הוספה/מחיקה, הרצה חדשה מאפשרת לבחור agent (`qa` — פורט של `file_qa.py`), **טמפרטורה** ו**פרומפט מערכת** חופשיים (ניסוי חי, לא רק בקוד), ניקוד ידני per-קריטריון בלחיצת כפתור, הפעלת judge (agent נפרד, מודל אחר לצמצום self-enhancement bias — כמו ב-`assignment2_judge.py`), ופאנל agreement שמראה בדיוק את אותו סוג ניתוח מ-`assignment2_writeup.md` (איפה מסכימים, איפה לא, ולמה).
- **מסך "מעבדת RAG"** — הגרסה האינטראקטיבית של מטלה 3, ובה כל שבע המשימות: תיאור הקורפוס וספירת הצ'אנקים (Task 1), הבייסליין ללא RAG בארבעה דליים (Task 1), מערך ההערכה עם **בדיקת כיסוי הקטגוריות שהמטלה דורשת מוצגת כמצב נמדד ולא כטענה** (Task 2), דפדפן צ'אנקים לצעד ה"actually look at it" — כולל דגימה אקראית וסינון md מול PDF, שבו נזקי ה-parsing נראים בעין (Task 3), מגרש משחקים לאחזור עם ציון דמיון לכל צ'אנק ו**צ'קבוקס לכל צ'אנק שקובע מה באמת נכנס לקונטקסט** (Task 4), תשובה מעוגנת שבה `[1]`/`[2]` הם לחיצים וקופצים לצ'אנק המצוטט וציטוט מומצא מסומן באדום, טבלת RAG מול בייסליין בפרוסות easy/hard (Task 5), ניתוח (א)/(ב)/(ג), ו-12 קונפיגורציות ה-sweep כגרף (Task 6).
- **בניית אינדקס מה-UI** — בחירת מסמכים, `chunk_size`/`overlap`, ומודל embedding, עם תצוגה מקדימה מיידית של מספר הצ'אנקים לפני שמשלמים דקות CPU. ואז **מדידת hit@k חיה על 32 השאלות בעלות המענה, בחינם**, שנוחתת על אותו גרף של ה-sweep המוקלט — כך שאפשר לכוונן ולראות אם שיפרת בלי לשרוף ולו קריאה אחת. האינדקס הקנוני `assignment3/index/` מוגן: בנייה כותבת ל-`index_custom/`, ומחיקה שלו מוחזרת כ-400.

### הרצה

שני שרתים, שני טרמינלים, שניהם משורש `tax-copilot/`:

```powershell
# טרמינל 1 — API (יוצר/מזרע את ה-DB אוטומטית בעליה הראשונה)
.venv\Scripts\activate
uvicorn api.main:app --reload --port 8000

# טרמינל 2 — קליינט
cd web
npm install   # פעם ראשונה בלבד
npm run dev
```

ואז פותחים `http://localhost:5173`. ה-API חייב GEMINI_API_KEY מאותו `.env` שמתואר למטה (המחשבון וה-`qa`/`judge` agents קוראים לו בדיוק כמו הסקריפטים).

#### מה עולה קריאות LLM ומה חינם

המכסה החינמית של Gemini היא 15 בקשות/דקה ו-500/יום, והיא כבר נשרפה פעם אחת באמצע Task 6. לכן ההפרדה הזו היא **גבול ארכיטקטוני** ולא משמעת: `api/rag/artifacts.py` ו-`api/rag/retrieval.py` אינם יכולים לבצע קריאה, ורק `api/rag/generation.py` יכול. התוצאה היא ששני שלישים מהתכונה נבדקים ב-pytest בלי מפתח API ובלי רשת.

| פעולה | עלות |
|---|---|
| אחזור, דפדוף בצ'אנקים, תצוגה מקדימה, בניית אינדקס, מדידת hit@k | **0** — embeddings מקומיים |
| כל טבלאות ההערכה של מטלה 3 | **0** — נקראות מקבצי התוצאה שעל הדיסק |
| "ענה מהקטעים שנבחרו" | 1 |
| "הפעל שופטים" על תשובה בודדת | 3–4 |
| הרצת טסט-לאב / judge על ריצה | קריאה לשאלה / ~4 לשורה |

כל כפתור שעולה מסומן בתגית עלות, ובראש מסך ה-RAG יש מונה קריאות יומי. הרצה של כל מערך ההערכה (~204 קריאות) **לא נחשפת ב-UI** בכוונה — היא נשארת ב-CLI, שם יש לה checkpointing.

#### פעולות ארוכות

בניית אינדקס, מדידת hit@k, הרצת טסט-לאב ושיפוט רצים כ-job ברקע (`api/jobs.py`) עם פס התקדמות אמיתי ("12 מתוך 28"), הערכת זמן וכפתור ביטול, במקום כפתור מושבת ושקט לשתי דקות. ביטול של שיפוט הוא בטוח: הוא מדלג ממילא על שורות ששופטו, כך שהפעלה חוזרת ממשיכה מאיפה שהפסיקה. ה-jobs נשמרים בזיכרון בלבד — `uvicorn --reload` מאבד אותם.

## נתונים (`data/` ו-`../TaxData/`)

- `data/tax_notes.md` — הבסיס למס שכיר 2026: מדרגות, נקודות זיכוי, ביטוח לאומי/בריאות, פנסיה, קרן השתלמות, סעיף 46, ודוגמאות מחושבות. כל מספר מגובה במקור (ראו `.claude/rules/tax-data-sourcing.md`).
- `data/tax_law_history.md` — הבסיס החוקי (סעיפי פקודת מס הכנסה) וציר זמן של שינויי חקיקה רלוונטיים לשכיר מ-2003 ואילך.

`data/` משרת את מטלות 1–2 ואת המחשבון (מסמך יחיד שנכנס במלואו לקונטקסט). קורפוס ה-RAG של מטלה 3 הוא נכס נפרד ברמת הריפו:

- `../TaxData/` — חמישה מדריכי md לפי תחום (שכירים, עצמאים, שוק ההון, מקרקעין, כללי) + `employees/income-tax-deductions-booklet-2026.pdf` (המסמך הרשמי של רשות המסים). מקורות ומגבלות אמינות מתועדים ב-`TaxData/README.md`.
- `assignment3/data/corpus_manifest.json` — מה נכנס לאינדקס: `doc_name`, נתיב (יחסית לשורש הריפו), פורמט ו-`source_url` לכל מסמך. זו נקודת הכניסה היחידה של `build_index.py` לקורפוס.
- `assignment3/index/` — אינדקס FAISS קנוני, **לקריאה בלבד**. בנייה מה-UI כותבת ל-`assignment3/index_custom/` (בgitignore).

## תשתית Agentic Engineering

לצד המטלות הממוספרות, הריפו הזה בונה בהדרגה שכבת `.claude/` (CLAUDE.md, rules, skills, agents, specs, hooks) לפי checklist נפרד. מצב מלא ומנומק — כולל מה דולג ולמה — ב-`IMPLEMENTATION.md`.

CI (`.github/workflows/claude.yml`) מריץ `pytest` על כל PR שנוגע ב-`tax-copilot/**`.

## סטאפ

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

הגדרת מפתח API (לכל סקריפט שקורא ל-Gemini — `hello_llm.py`, `file_qa.py`, סקריפטי מטלה 2, וגם שרת ה-`api/` — `local_llm.py` בלבד לא צריך מפתח, כי הוא רץ מודל מקומי). מפתח Gemini מתקבל ב-[aistudio.google.com](https://aistudio.google.com) → Get API key.

המפתח נשמר מקומית בקובץ `.env` (לא נכנס לגיט — כלול ב-`.gitignore`) ונטען אוטומטית ב-`load_dotenv()`. פשוט פתחו את `.env` והדביקו את המפתח:

```
GEMINI_API_KEY=AIza...
```

מטלה 3 מוסיפה תלויות כבדות (`faiss-cpu`, `sentence-transformers`, `langchain*`, `pypdf`, `rank_bm25`) שכבר כלולות ב-`requirements.txt`. ה-embeddings רצים **מקומית ובלי מפתח API** — בהרצה הראשונה של `build_index.py` יורד `intfloat/multilingual-e5-small` מ-HuggingFace לקאש המקומי (פעם אחת, דורש רשת).

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

### מטלה 3 (RAG) — סדר הרצה

```powershell
python src\build_index.py                       # בונה FAISS + מדפיס 10 צ'אנקים ו-3 שאילתות בדיקה
python src\assignment3_generate_eval.py         # 28 שאלות סינתטיות (~30 קריאות)
python src\assignment3_build_eval_set.py        # ממזג עם hard_questions.csv -> 34 שאלות
python src\rag_pipeline.py                      # sanity: 2 השאלות הבלתי-ניתנות-למענה חייבות לסרב
python src\assignment3_baseline.py              # Task 1 - בייסליין ללא RAG
python src\assignment3_run_rag.py               # Task 4
python src\assignment3_evaluate.py              # Task 5 (--resummarise מחשב מחדש בלי שופטים)
python src\assignment3_analysis.py              # (א)/(ב)/(ג), 0 קריאות
python src\assignment3_experiments.py           # Task 6 שלב א: sweeps, 0 קריאות
python src\assignment3_experiments.py --phase-b # Task 6 שלב ב: ניסויים מלאים (יקר)
python src\assignment3_judge_recalibration.py   # מדידת המכשיר: השופט המתוקן מול הישן
```

### בדיקות

```powershell
pytest
```

`tests/test_rag_backend.py` מכסה את החצי החינמי של ה-RAG (אחזור, ציוני דמיון, ארטיפקטים) — רץ **בלי `GEMINI_API_KEY` ובלי רשת**, מה שאפשרי רק בגלל שהפיצול ב-`api/rag/` הוא לפי עלות. `tests/test_llm_json_repair.py` מכסה את תיקון הגרשיים העבריים ב-JSON.
