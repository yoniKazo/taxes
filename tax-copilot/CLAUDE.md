# CLAUDE.md — tax-copilot

## Forbidden
- לחשוף/להדפיס ערכי API keys, או לקומיט `.env` (רק `.env.example` עם ערך ריק נכנס לגיט).
- להמציא או לשנות מספרי מס ב-`data/tax_notes.md` בלי מקור ברשימת המקורות בתחתית הקובץ.
- להריץ את מטריצת ה-27 השילובים של `qa_experiment.py` מול המודל המקומי (`bloomz-560m`) — הוא רץ **פעם אחת בלבד** כרפרנס, כי כל קריאה מקומית לוקחת דקות על CPU (הסיבה מתועדת ב-`experiment_results.md`).
- לתייג שאלה כ-`answerable=False` במערך ההערכה של assignment3 על סמך חיפוש בקבצי md בלבד — הבדיקה חייבת לכסות את כל 151 הצ'אנקים, כולל ה-PDF (ראו CODIFY 2026-08-18).
- להחליף מכשיר מדידה (שופט, מדד, prompt של judge) באמצע ניסוי מתמשך ולהשוות מספרים חדשים לישנים — לתקן קדימה ולמדוד את המכשיר בנפרד, כמו ב-`assignment3_judge_recalibration.py`.
- לקבע שם מודל Gemini מתוארך (למשל `gemini-2.0-flash`) — שמות כאלה כבר קרסו ב-404; להשתמש רק ב-alias לא מתוארך כמו `gemini-flash-lite-latest`.

## Conventions
- עברית לפרומפטים/תיעוד/הודעות; אנגלית למזהי קוד (functions, variables).
- כל סקריפט חדש שקורא ל-LLM מתארח עוקב אחרי הדפוס הקיים ב-`hello_llm.py`/`file_qa.py`/`qa_experiment.py` (ראו `.claude/skills/add-llm-script/`).
- `sys.stdout.reconfigure(encoding="utf-8")` בתחילת כל סקריפט שמדפיס עברית (אחרת קריסה על cp1255 בווינדוס).
- קילוף ```` ``` ```` code fences לפני `json.loads`/`pydantic` — Gemini לפעמים עוטף JSON ב-markdown fence גם כשמתבקש "JSON בלבד".
- Type hints על חתימות פונקציות; ללא docstrings ארוכות — שורה אחת רק כשלא ברור מהשם.

## Stack & architecture
- Python + `.venv` (`requirements.txt`: openai, pydantic, python-dotenv, transformers, torch, fastapi, uvicorn, pytest; ומ-assignment3 גם langchain / langchain-community / langchain-huggingface, sentence-transformers, faiss-cpu, pypdf, rank_bm25).
- ספק מתארח: Gemini, דרך `openai` SDK מול endpoint תואם-OpenAI (`base_url=".../v1beta/openai/"`) — לא SDK ילידי, כי לא הייתה גישה לקונסולת Anthropic.
- `pydantic` ל-validation של structured output (`hello_llm.py`).
- מודל מקומי: `bigscience/bloomz-560m` דרך `transformers.pipeline`, בלי API key (`local_llm.py`).
- `python-dotenv` טוען `GEMINI_API_KEY` מ-`.env` (בgitignore).
- RAG מלא קיים מ-assignment3: FAISS + `RecursiveCharacterTextSplitter(1000/150)` + embeddings מקומיים, מעל 6 מסמכים ב-`TaxData/` (5 md + PDF רשמי). **`TaxData/` יושב מחוץ ל-`tax-copilot/`, ברמת הריפו** — הנתיבים ב-`assignment3/data/corpus_manifest.json` יחסיים לשורש הריפו ולא לתיקיית הפרויקט; המניפסט הוא נקודת הכניסה היחידה לקורפוס, וקובץ שנוסף ל-`TaxData/` בלי עדכון שלו פשוט לא יאונדקס. ראו `src/build_index.py`, `src/rag_pipeline.py`. `file_qa.py` נשאר כפי שהוא — single-doc grounding, התוצר של מטלה 1.
- **מודל embedding: `intfloat/multilingual-e5-small`, לא bge-small-en.** קורפוס עברי — מודל אנגלי-בלבד נותן hit@k של 0.719 מול 0.969 (נמדד על 32 שאלות). prefix conventions שונים לכל מודל ומרוכזים ב-`src/embeddings.py`.
- **RAG ב-UI** (`/rag` בקליינט): `api/rag/` מפוצל לפי **עלות**, לא לפי נושא — `artifacts.py` (קבצי תוצאה), `retrieval.py` (אינדוקס/אחזור/hit-rate) ו-`generation.py` (תשובה + שופטים). רק השלישי יכול לשרוף מכסה, ולכן שני הראשונים נבדקים ב-pytest בלי `GEMINI_API_KEY` ובלי רשת. `api/jobs.py` מריץ את הפעולות הארוכות (בניית אינדקס, hit@k, הרצת טסט-לאב, שיפוט) עם התקדמות וביטול.
- **`assignment3/index/` לקריאה בלבד.** זה האינדקס הקנוני שכל סקריפטי המטלה טוענים. בנייה מה-UI כותבת ל-`assignment3/index_custom/<slug>/` (בgitignore), ו-`DELETE /rag/indexes/default` מוחזר כ-400.

## Command cheatsheet
### הרצת האפליקציה (שני טרמינלים)
```powershell
# טרמינל 1 — שרת (מתיקיית tax-copilot)
uvicorn api.main:app --reload --port 8000

# טרמינל 2 — קליינט
cd web; npm install; npm run dev             # http://localhost:5173
```
טאבים: `/calculator` (מטלה 1), `/lab` (מטלה 2), `/rag` (מטלה 3).

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src\hello_llm.py
python src\file_qa.py data\tax_notes.md "שאלה"
python src\local_llm.py
python src\qa_experiment.py
```

### assignment3 (RAG) — סדר הרצה
```powershell
python src\build_index.py              # בונה FAISS + מדפיס 10 צ'אנקים ו-3 שאילתות בדיקה
python src\assignment3_generate_eval.py    # 28 שאלות סינתטיות (~30 קריאות)
python src\assignment3_build_eval_set.py   # ממזג עם hard_questions.csv -> 34 שאלות
python src\rag_pipeline.py             # sanity check: 2 השאלות הבלתי-ניתנות-למענה חייבות לסרב
python src\assignment3_baseline.py     # Task 1
python src\assignment3_run_rag.py      # Task 4
python src\assignment3_evaluate.py     # Task 5 (--resummarise מחשב מחדש בלי שופטים)
python src\assignment3_analysis.py     # (a)/(b)/(c), 0 קריאות
python src\assignment3_experiments.py            # Task 6 שלב א: sweeps, 0 קריאות
python src\assignment3_experiments.py --phase-b  # Task 6 שלב ב: 3 ניסויים מלאים
```

## Open questions
- ~~אין retrieval אמיתי~~ — נסגר ב-assignment3 (ראו Stack & architecture).
- `evidence_page`/`section` בצ'אנקים של md נגזר מהכותרת שלפני **תחילת** הצ'אנק; צ'אנק שמשתרע על כמה סעיפים מתויג לפי הראשון. לכן hit-rate מחושב ברמת `doc_name` ולא ברמת סעיף. שיפור אפשרי: תיוג לפי כל הכותרות שהצ'אנק חוצה.
- Task 6 שלב ב' הורץ חלקית: `exp1` (k=8) — יצירה מלאה + שיפוט 6/34 שורות; `exp2` (bge) — יצירה בלבד; `exp3` (hybrid) — לא רץ. העצירה היא **תקרה יומית של 500 קריאות**, שאותה throttling לא פותר. `assignment3_experiments.xlsx` לא נוצר, כי `run_phase_b()` בונה אותו רק בסוף ריצה מלאה. הניתוח שכן ניתן להפקה בחינם מהקבצים השמורים מתועד ב-writeup.
- **`exp1_top_k_8_judged.json` שופט במכשיר המתוקן** (`judges.py` תוקן 18.8 23:43, השיפוט נכתב 19.8 01:33), בעוד ש-Task 5 שופט בישן. לכן דלתא ב-`faithfulness` בין השניים אינה בת-השוואה. אין שדה `judge_version` בקבצי התוצאה — זו הסיבה שהפער התגלה רק מחותמות זמן.
- `.claude/rules/tax-data-sourcing.md` מכסה `data/**/*.md` בלבד, ולכן **אינו חל על `TaxData/`** — שיושב מחוץ לתיקיית הפרויקט (rules לא מגיעים ל-`../`) ומכיל מספרי מס לארבעה תחומים נוספים מעבר לשכירים. עריכה של `TaxData/` היא עריכה של קורפוס ה-RAG: היא לא מגובה בכלל sourcing אוטומטי, ו**מחייבת בנייה מחדש של `assignment3/index/`** אחרת האינדקס והמקור יתפצלו בשקט.
- **הריפו הוא `taxes` (`github.com/yoniKazo/taxes.git`), ו-`tax-copilot/` היא תת-תיקייה בו — לא repo נפרד.** `origin/master` קיים ומעודכן. אין עדיין CI: S6 (Claude Code ב-CI) כבר **אינו חסום**, רק לא בוצע. workflow ייכתב ב-`.github/workflows/` שברמת שורש הריפו עם `working-directory: tax-copilot`.
- איכות המודל המקומי חלשה (`bloomz-560m`, נבחר כי כבר מותקן, לא לאיכות) — לשקול מחדש לפני שימוש user-facing.
- Scope נוכחי: שכירים בלבד. הרחבה לעצמאים היא החלטה עתידית, לא ברירת מחדל.
- `src/tax_refund_calculator.py` מקשיח את מדרגות המס/אחוזי ביטוח לאומי/שווי נקודת זיכוי כקבועים בקוד (עם הערת מקור inline) — duplication מודע מול `data/tax_notes.md`, כי `.claude/rules/tax-data-sourcing.md` מוגבל ל-`paths: data/**/*.md` ולא חל על `.py`. אם `tax_notes.md` יתעדכן לשנת מס חדשה, הקבועים בקוד לא יתעדכנו אוטומטית.

## CODIFY log
תיעוד כשלים אמיתיים שנתקלנו בהם בפועל, עם תאריך ונימוק לתיקון (חלק מ-PLAN→DELEGATE→ASSESS→CODIFY). ראו גם entry נוסף ב-`.claude/rules/hosted-llm-quota.md`.

- **2026-08-12** — `gemini-2.0-flash` (שם מודל מתוארך) החזיר 404 באמצע עבודה על `hello_llm.py`. נימוק: Google מוציא משימוש dated snapshots בלי אזהרה מוקדמת ניכרת. תיקון: מעבר ל-alias לא מתוארך (`gemini-flash-lite-latest`) — כבר משוקף ב-Forbidden למעלה.
- **2026-08-12** — הדפסת פלט עברי קרסה על Windows (ברירת המחדל cp1255 לא תומכת בכל התווים). נימוק: `sys.stdout` לא unicode כברירת מחדל בטרמינל Windows. תיקון: `sys.stdout.reconfigure(encoding="utf-8")` בתחילת כל סקריפט — כבר משוקף ב-Conventions.
- **2026-08-12** — תשובת JSON/Pydantic מ-Gemini הגיעה עטופה ב-```` ``` ```` markdown fence וקרעה את `json.loads`, למרות בקשה מפורשת ל-"JSON בלבד" בפרומפט. נימוק: Gemini לא אמין ב-100% בציות להוראת "בלי fence". תיקון: קילוף fence לפני parse — כבר משוקף ב-Conventions.
- **2026-08-18** — Gemini מחזיר גרשיים עבריים (`מע"מ`, `בע"מ`, `דו"ח`) **לא-מוברחים** בתוך מחרוזות JSON, ובאופן לא-עקבי: באותה תשובה עצמה `sources` היה מוברח נכון ו-`answer` לא. `response_format={"type":"json_object"}` לא פותר (נבדק, פלט זהה). נימוק: מונחי מס בעברית מלאים בגרשיים, כך שזה מסלול ראשי ולא פינה נדירה. תיקון: `llm.repair_json_quotes()` — מנסה קודם parse רגיל ורק אז מתוקן, כך שלא ניתן לקלקל תשובה תקינה.
- **2026-08-18** — שאלת "unanswerable" במערך ההערכה תויגה כך על סמך grep במדריכי ה-md בלבד; ה-PDF בקורפוס דווקא הכיל את התשובה, וה-RAG ענה נכון ונראה כמזייף. נימוק: תיוג ground-truth שלא נבדק מול **כל** הקורפוס בודק את הזיכרון של הכותב, לא את המערכת. תיקון: כל תווית `answerable=False` נבדקת מול כל הצ'אנקים אחרי בניית האינדקס, לא לפניה.
- **2026-08-19** — הרצת Task 6 נתקעה: 136 קריאות שופט שאמורות לקחת 12 דקות רצו 90 דקות בלי להסתיים. הסיבה: `judge_rag_row` יורה **4 קריאות ברצף** לכל שורה עם `throttle()` אחד בלבד — כ-24 בקשות/דקה מול תקרה של 15. כל קריאה נכשלה ב-`RateLimitError`, ישנה 15 שניות, וניסתה שוב. נימוק: throttling באחריות הקורא נשבר ברגע שקורא אחד עושה יותר מקריאה אחת לאיטרציה — וזה בדיוק מה ש-4 שופטים עושים. תיקון: `_wait_for_slot()` **בתוך** `llm.call_text` (רצפה של 4.2 שניות בין קריאות), כך שהכלל נאכף מבנית; בנוסף checkpointing לכל שורה משופטת, כדי שהפסקה לא תמחק שעת עבודה.
- **2026-08-18** — `judge_faithfulness` נבנה בלי לראות את השאלה (למניעת reasoning אחורה), ולכן דירג **סירובים נכונים** כ-`bad` — הוא שפט אותם מול נושא הצ'אנק במקום מול השאלה. עלות נמדדת: faithfulness בפרוסה הקשה 0.333 במקום 0.500. נימוק: סיכון הדליפה נמצא ב-reference answer, לא בשאלה. תיקון: השאלה מועברת ל-judge; המכשיר הישן **לא** הוחלף רטרואקטיבית באמצע ניסוי — נמדד בנפרד ב-`assignment3_judge_recalibration.py`.
- **2026-08-20** — שלוש מלכודות שהתגלו בהעברת ה-RAG ל-UI, כולן **מחזירות תשובה שגויה בשקט** במקום לזרוק שגיאה:
  1. `assignment3_experiments.build_hybrid_retriever` מקודד קשיח `chunks_for()` (1000/150) ו-`load_index()` (האינדקס הקנוני). קריאה שלו כשהמשתמש בחר אינדקס מותאם מחזירה תוצאות מקורפוס אחר מזה שעל המסך. תיקון: תאום מפורש ב-`api/rag/retrieval.hybrid_retriever` שמקבל vectorstore; הסקריפט המקורי לא נגעו בו.
  2. `similarity_search_with_score` ב-FAISS מחזיר **מרחק L2** (קטן=טוב), לא דמיון. מד התקדמות שמחובר אליו ישירות מצייר את הצ'אנק הטוב ביותר כעמודה הריקה ביותר. הווקטורים מנורמלים, ולכן `cos = 1 - L2²/2`. יש בדיקת מונוטוניות ב-`tests/test_rag_backend.py`.
  3. `EnsembleRetriever` (hybrid) לא מחזיר ציון השוואתי כלל — מדווח `null` ולא מספר מומצא.
- **2026-08-20** — `src/llm.py` בנה את לקוח ה-OpenAI **בזמן import** מ-`os.environ["GEMINI_API_KEY"]`, כך ש-`import` של כל מודול ב-`src/` הפיל את uvicorn בלי מפתח והפך את החצי החינמי של ה-RAG לבלתי-בדיק. נימוק: ה-FastAPI מייבא את המודולים האלה גם כדי לקרוא CSV, עבודה שעולה אפס קריאות. תיקון: `llm.get_client()` עצל — אותה התנהגות, רק לא ב-import.
- **2026-08-20** — משמר הציטוטים הדטרמיניסטי של Task 4 (`\[(\d+)\]`) **פספס ציטוטים מקובצים**. המודל כותב גם `[1, 2, 8]` ולא רק `[2]`, והתבנית לא תופסת לא את הקבוצה ולא את המספרים שבתוכה — כך ש-`[8]` מתוך 5 קטעים שסופקו עבר בשקט. נתפס בבדיקת דפדפן חיה, לא בסקריפטים. נימוק: זו בדיוק הצורה שבה מספר מחוץ לטווח מסתתר, כי היא נראית כמו ציטוט תקין. תיקון: `rag_pipeline.CITATION_RE` תופס גם קבוצה ומחלץ ממנה כל מספר; אותה תבנית ב-`GroundedAnswerPanel` מרנדרת כל מספר כצ'יפ נפרד. **34 השורות השמורות נבדקו מחדש מול המשמר המתוקן ונשארו 0** — המספר שדווח ב-writeup לא משתנה.
