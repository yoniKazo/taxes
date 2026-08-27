# מטלה 4 — Agents

**Baseline קפוא (Task 1):** commit `39692df` — `assignment3/index/` (FAISS, `multilingual-e5-small`, chunk 1000/150), k=5, מחולל `gemini-flash-lite-latest`, `RAG_SYSTEM_PROMPT` ב-`src/rag_pipeline.py`. לא נגעו בו בזמן בניית ה-agent.

**תפקידים:** Agent = `claude-haiku-4-5`, Judge (evaluator-optimizer + Task 5) = `claude-sonnet-5`, שניהם דרך Anthropic native SDK (לא Gemini — ראו CLAUDE.md, `truststore.inject_into_ssl()` נדרש בשל TLS-inspection עצמי ברשת).

---

## Task 2 — שלושת ה-tools

| Tool | Scope | לא מכסה | חוזה כישלון |
|---|---|---|---|
| `search_tax_corpus` | 6 מסמכי המס הישראלי (מטלה 3) | חדשות/עדכוני חוק אחרי איסוף הקורפוס, חישוב | `NO_RESULTS: <query>` |
| `calculator` | ביטויים אריתמטיים כלליים (`+ - * / ** %`, סוגריים) | משתנים, פונקציות, כל דבר מעבר לאריתמטיקה | `ERROR: <הסבר>` |
| `calculate_tax_refund` | מס הכנסה/ביטוח לאומי/בריאות לשכיר, שנת 2026 | עצמאים, רווחי הון, מס שבח/רכישה, מע"מ | `ERROR: <הסבר>` |

`calculator` בנוי על `ast`-parsing עם whitelist מפורש (לא `eval()` גולמי) — הקלט מגיע מ-LLM, וריצת קוד שרירותי היא סיכון אמיתי.

**מבחן "המהנדס הטיפש":** בוצע דרך קריאת API נקייה (`claude-sonnet-5`, בלי `system` prompt, בלי הקשר על הפרויקט — לא subagent בתוך הריפו הזה, כי הוא היה יורש את `CLAUDE.md`). קיבל רק את שלושת תיאורי ה-tools + משימה אחת ("לשכיר עם משכורת 22,000 ₪... שתורם 4,000 ₪ בשנה, מה הנטו החודשי?"). **תוצאה: בחר `calculate_tax_refund` עם הארגומנטים המדויקים (`gross_salary=22000, gender='male', annual_donation=4000`) בניסיון הראשון.** לא נדרש תיקון תיאור.

---

## Task 3 — הלולאה

`raw_loop.py` הורץ פעם אחת על משימת multi-hop אמיתית (mh6 — שכיר מול עצמאי). **ממצא אמיתי, לא רק "זה עבד":** הלולאה הידנית קראה שלוש פעמים ל-`search_tax_corpus`, מצאה את השיעורים הנכונים (12.17%/18%), אך **חישבה לא נכון** — הפעילה את השיעורים כאחוז שטוח על כל ה-20,000 ₪ במקום לכבד את מבנה המדרגה (7,703 ₪ הראשונים בשיעור אחד, השאר בשיעור אחר), והגיעה ל-1,166 ₪ הפרש במקום 981.13 ₪ הנכונים. **זה בדיוק סוג הכשל שהמטלה מבקשת ש-Task 5 יתפוס** — לא בעיית אחזור, בעיית reasoning אריתמטי על מידע שכבר אוחזר נכון. (הלולאה הידנית לא נגעה בה שוב אחרי זה, כנדרש.)

`agent.py` (LangGraph): dry run 3 משימות × הרצה אחת עבר בהצלחה — ~15,000 טוקנים ממוצע למשימה. שלוש רשתות הביטחון (max_iterations, token_budget, timeout) מיושמות ונבדקו לוגית. שתי משימות ה-`tool_fails` אומתו ידנית: בשני המקרים ה-agent קרא ל-tool השבור **פעם אחת בלבד**, קיבל את מחרוזת ה-`ERROR`, ודיווח סירוב נקי (`terminal_state=refused`) — לא הסתחרר בלולאה ולא המציא תשובה.

---

## Task 4 — Evaluator-Optimizer

Reuse ישיר של הרוברייק **האמיתית** של מטלה 2 (`assignment2_rubric.md` — 6 קריטריונים, pass bar 4/6 good + 0 bad, go/no-go על grounding/length), מועברת ל-`claude-sonnet-5`. `document` היחיד שה-QA judge המקורי ציפה לו הוחלף בהקשר תוצאות ה-tools מה-trace.

**באג תשתית אמיתי שנתפס תוך כדי בנייה, לפני שהגיע ל-Task 5:** `claude-sonnet-5` מפעיל כברירת מחדל extended thinking, שיכול לצרוך את **כל** תקציב ה-`max_tokens` על בלוק החשיבה בלבד — `stop_reason="max_tokens"`, תוכן=`[ThinkingBlock]` בלבד, טקסט גלוי ריק. תוקן עם `thinking={"type": "disabled"}` בכל קריאת judge (הרוברייק כבר מבקשת explanation-לפני-verdict בתוך ה-JSON הגלוי, כך שאין צורך בבלוק חשיבה נפרד). ממצא שני: עם `tool_outputs` ארוכים, המודל לפעמים כותב פרוזה לפני ה-JSON למרות ההוראה "אך ורק JSON" — טופל בחילוץ `{...}` החיצוני ביותר מהטקסט הגולמי, לא רק בקילוף code-fence.

(טבלת לפני/אחרי + פסקת פסיקה: להשלים אחרי הרצת Task 5 המלאה.)

---

## Task 5 — RAG מול Agent

> **סטטוס: RAG (קונפיגורציה A) הושלם במלואו על כל 24 המשימות × 5 הרצות (120 שורות). צד ה-Agent נעצר ב-Anthropic credit balance ריק אחרי שהושלם על 15/24 משימות + 2/5 הרצות של משימה 16 — ראו "אירוע: נגמר קרדיט Anthropic" למטה. הטבלה הסופית ו-(a)-(e) ימולאו לאחר שהמשתמש יטען קרדיט וה-agent side ירוץ מחדש (checkpointing כעת מונע איבוד עבודה חוזר).**

### מה שכבר ידוע מ-RAG לבדו (5/5 הרצות לכל משימה, דטרמיניסטי כמעט לחלוטין)

| סוג משימה | good | bad | n |
|---|---|---|---|
| multi_hop | 10 | 20 | 30 |
| single | 25 | 25 | 50 |
| unanswerable | 15 | 0 | 15 |
| no_tool / tool_fails | n/a | n/a | 40 (25 שורות, structurally meaningless) |

**ממצא איכותני אמיתי, לא רק מספר:** RAG "bad" על multi_hop הוא **תמיד** 5/5 (mh1, mh3, mh4, mh6) או **תמיד** good 5/5 (mh2, mh5) — אין שונות בין הרצות, כי RAG של מטלה 3 דטרמיניסטי-כמעט-לגמרי. אבל mh2 ("מע"מ 18% על 4,390 ₪") ו-mh5 ("היטל השבחה 50%") יצאו **good** למרות ש-RAG אין לו מחשבון בכלל! ההסבר: אלה חישובי אחוזים חד-שלביים פשוטים (כפל אחד) שה-LLM (Gemini) פתר נכון "בראש", בלי tool — לעומת mh1/mh3/mh4/mh6 שדורשים גם לזהות איזו מדרגה/שיעור רלוונטי מתוך כמה חלופות בקורפוס (למשל מס רכישה: 4 מדרגות שונות תלויות-הקשר) *וגם* לחשב. **המסקנה הזמנית: RAG לא נכשל על "צריך לחשב" — הוא נכשל על "צריך לבחור את המספר הנכון מתוך כמה, ואז לחשב עליו".** זה בדיוק סוג הכשל ש-Task 5(a) (זכיית ה-agent) אמור להדגים במלואו ברגע שצד ה-agent ירוץ.

Single: בדיוק חצי-חצי, וה-5 המשימות ש-`bad` (s1, s4, s6, s9, s10) הן **בדיוק** אלו שנבנו ב-Task 1 להזדקק ל-`calculate_tax_refund`/`calculator` בלבד (ללא retrieval) — RAG לא יכול לפתור אותן מבנית, לפי העיצוב. Unanswerable: 15/15 good — RAG ממשיך להיות חזק בסירוב נכון (עקבי עם מטלה 3).

### מה שכן נאסף מ-Agent לפני העצירה (15/24 משימות, 5/5 הרצות; לא נשמר ל-xlsx, ראו האירוע למטה -- מדווח מה-console log בלבד)

| task_id | סוג | agent success (5 הרצות) | agent terminal_state |
|---|---|---|---|
| mh1, mh3, mh4 | multi_hop | good ×5 | answered ×5 |
| mh2 | multi_hop | good ×5 | answered 2, **cap_breached 3** |
| mh5 | multi_hop | good ×5 | answered ×5 |
| mh6 | multi_hop | **bad ×5** | **cap_breached ×5** |
| nt1, nt2, nt3 | no_tool | good ×5 | answered ×5 |
| ua1 | unanswerable | bad ×4, good ×1 | cap_breached ×4, refused ×1 |
| ua2 | unanswerable | good ×3, bad ×2 | refused ×3, cap_breached ×2 |
| ua3 | unanswerable | **bad ×5** | **answered ×5 (לא refused!)** |
| tf1 | tool_fails | good ×5 | refused ×5 |
| tf2 | tool_fails | good ×2, bad ×3 | refused ×2, answered ×3 |
| s1, s2 (2/5) | single | good | answered |

**שלושה ממצאים אמיתיים שכבר עולים מזה, לפני שממשיכים:**
1. **mh1/mh3/mh4/mh5 הם בדיוק המקרים ש-RAG נכשל בהם וה-agent הצליח ב-100% מההרצות** — זה למעשה כבר ה-Task 5(a) המבוקש ("task the agent won that RAG structurally could not do"), רק שצריך את ה-trace המלא (מ-`assignment4/data/traces/mh1.jsonl` וכו', שכן נשמרו בשלמותם) כדי לצטט אותו נכון.
2. **mh6 (הכי קשה, 3 tools יחד) נכשל 5/5 עם cap_breached** — עקבי עם מה ש-`raw_loop.py` הידני כבר הראה (Task 3): retrieval נכון, אבל reasoning אריתמטי/מבני שגוי (לא מכבד את מבנה המדרגה) גורם ל-agent "להסתבך" בניסיון לתקן את עצמו דרך ה-evaluator-optimizer עד שהוא חורג ממספר האיטרציות. מועמד חזק ל"הכישלון הגרוע ביותר" (traces נדרשים, Task 5.4).
3. **ua3 ("מה מזג האוויר מחר בתל אביב?") ענה 5/5 במקום לסרב** — זה **false_answer** על unanswerable, הכי חמור מבין כל כשלי הסירוב, ומעיד שה-agent לא מזהה "שאלה שאינה קשורה בכלל למיסוי" כמצדיקה סירוב מיידי כמו RAG (ש-100% הצליח על אותה קטגוריה). worth בדיקה ישירה ברגע שהאשראי יחודש.

---

## אירוע: נגמר קרדיט Anthropic באמצע Task 5

**מה קרה:** ריצת `assignment4_eval_runner.py --runs 5` (24 משימות × 5 הרצות × 2 קונפיגורציות) נכשלה אחרי 15 משימות מלאות + 2/5 הרצות של משימה 16, עם `anthropic.BadRequestError: Your credit balance is too low to access the Anthropic API`. חשבון Anthropic-י מדובר, לא bug בקוד.

**נימוק לתיקון:** `run_matrix()` צבר את כל השורות ב-list בזיכרון (`rows.append(...)`) וכתב ל-xlsx רק ב-`__main__` בסוף הריצה כולה — בדיוק הלקח שכבר תועד ב-`CLAUDE.md` CODIFY (2026-08-19, מטלה 3 Task 6): "checkpointing לכל שורה משופטת, כדי שהפסקה לא תמחק שעת עבודה". הלקח לא יושם כאן מלכתחילה, ונלמד שוב ביוקר — 15 משימות ששולם עליהן בפועל אבדו מה-xlsx (נותרו רק ב-console log, לא ב-JSONL traces של הצד המצטבר).

**תיקון:** `assignment4_eval_runner.py` כותב כעת כל שורה (RAG ו-agent) ל-`assignment4/data/matrix_checkpoint.jsonl` **מיד** אחרי שהיא מחושבת, ו-`run_matrix(resume=True)` (ברירת מחדל) מדלג על כל (task_id, run, config) שכבר ב-checkpoint. תוסף גם `--configs rag`/`--configs agent` להרצת צד אחד בלבד -- מה שאיפשר לשחזר את כל צד ה-RAG (Gemini, לא מושפע מהקרדיט) ב-120 שורות מיד אחרי האירוע, בלי לחכות לחידוש האשראי.

**מה עדיין חסר:** צד ה-agent המלא (24 משימות, לא רק 15) יצטרך לרוץ מחדש במלואו ברגע שהקרדיט יחודש -- ה-15 שכבר רצו לא ניצלו מה-checkpointing כי הוא נוסף רק אחרי האירוע. עלות משוערת זהה להערכה המקורית (~$10-15).

---

## Task 6 — שני ניסויים

_להשלים אחרי ניתוח כשלי Task 5 בפועל — השערות חייבות להיות מעוגנות בכשל שנצפה, לא בניחוש._

---

## הפסקה הסופית

_להשלים: agent או workflow, עם המספר הספציפי שהכריע._
