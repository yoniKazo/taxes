# תוכנית — מטלה 3 (RAG) ל-tax-copilot

## הקשר

`HomeWork/assignment3.md` (Lecture 3 · RAG & Grounding) מבקש להחליף את הגישה של מטלה 1 (`file_qa.py` — הזנת מסמך שלם לפרומפט) ב-RAG אמיתי: אינדקס וקטורי, retrieval, ואת כלי ההערכה שנבנו במטלה 2 כדי להוכיח במספרים אם RAG בכלל עזר. זו אותה ריפו (`c:\Repo\Taxes`, גיט יחיד בשורש — לא ריפו נפרד כפי ש-`plans/assignment1-plan.md` הניח בטעות), אותו תחום (ייעוץ מס ישראלי, עברית).

התוכנית הזו מכסה Tasks 1–6 של המטלה (Task 7 בונוס — לא בסקופ). כל ההחלטות הפתוחות סוכמו עם המשתמש (ראו §0).

## 0. החלטות שננעלו

| נושא | החלטה |
|---|---|
| קורפוס | 5 מדריכי `TaxData/*/*.md` הקיימים **+ PDF רשמי שישי** (רשות המסים, "לוח עזר לחישוב מס הכנסה ממשכורת ינואר 2026", 32 עמ' — כבר מצוטט כמקור #1 ב-`employees-tax-guide.md`) |
| FAISS index | **נשמר בגיט** (לא ב-gitignore) — `assignment3/index/` מחויב יחד עם הקוד |
| 24 שאלות סינתטיות | **סקריפט אוטומטי מול Gemini** (`gemini-flash-lite-latest`, ~24 קריאות, throttled) |
| מודל embedding לניסוי 1 (Task 6) | `intfloat/multilingual-e5-small` |
| Generator / Judge | `gemini-flash-lite-latest` / `gemini-3.1-flash-lite` — אותו זוג מודלים lite-tier ממטלה 2 (נמנעים מ-20-req/day trap של טייר רגיל, ראו `.claude/rules/hosted-llm-quota.md`) |

## 1. קורפוס

הורדת ה-PDF ל-`TaxData/employees/income-tax-deductions-booklet-2026.pdf` (URL: `https://www.gov.il/BlobFolder/generalpage/income-tax-monthly-deductions-booklet/he/generalInformation_income-tax-monthly-deductions-booklet_monthly-deductions-booklet-2026.pdf`).

`TaxData/` נשאר בשורש (sibling של `tax-copilot/`) — **לא** מועתק לתוך `tax-copilot/`. `build_index.py` קורא ממנו דרך נתיב יחסי.

מניפסט: `tax-copilot/assignment3/data/corpus_manifest.json` — רשימת 6 המסמכים (`doc_name`, `path`, `format`, `topic`, `source_url`). כל סקריפט (index, eval-gen, baseline) נגזר מהמניפסט, לא מרשימה קשיחה בקוד.

> **גילוי נאות ל-write-up**: ~900 שורות md + 32 עמ' PDF **כן** נכנסים לחלון ההקשר של Gemini (1M טוקנים), בניגוד לרוח הדרישה "does not fit comfortably in one prompt". לכתוב זאת במפורש במטלה במקום למכור את זה אחרת — הפואנטה הפדגוגית כאן היא ה-workflow (retrieve מול paste-everything) ומדידת ההפרש, לא גלישה אמיתית מהקשר. זו אותה עמדת שקיפות שנקטנו במטלה 2 לגבי Claude→Gemini.

## 2. Eval set — `tax-copilot/assignment3/data/tax_rag_eval_set.csv`

עמודות: `id, question, reference_answer, evidence_doc, evidence_page, answerable, difficulty, category`.
- `evidence_doc`/`evidence_page`: לצ'אנקים מ-md — שם הסקשן (heading); ל-PDF — מספר עמוד אמיתי. לשתי שאלות ה-multi-hop — ערכים מופרדים ב-`;` (multi-doc ground truth), וקוד ה-hit-rate (§6) יודע לפרש זאת.
- `category`: עמודת מעקב פנימית (`synthetic`/`multi-hop`/`unanswerable`/`negation`/`identifier`) — עוזרת ל-Task 5(c) ול-Task 6.

### 24 שאלות סינתטיות (`difficulty=easy`)

סקריפט `tax-copilot/src/assignment3_generate_eval.py`:
1. טוען מניפסט, מריץ את אותו `RecursiveCharacterTextSplitter(1000, 150)` שמשמש את `build_index.py` (מייבא את פונקציית ה-splitting משם — לא לשכפל).
2. דוגם ~4 צ'אנקים לכל מסמך (`random.seed` קבוע לreproducibility), מדלג על צ'אנקים קצרים מ-~200 תווים.
3. קריאת Gemini אחת לכל צ'אנק: "הנה קטע ממדריך מס; כתוב שאלה אחת שמשתמש אמיתי היה שואל וקטע זה עונה עליה, ואת התשובה המדויקת; JSON `{question, reference_answer}`". אותו דפוס throttle/retry/fence-stripping כמו `assignment2_generate.py`.
4. `evidence_doc`/`evidence_page` נלקחים ממטא-דאטה של הצ'אנק (תלוי ב-metadata enrichment של `build_index.py`, לכן build_index צריך לרוץ/להיות importable קודם).
5. מעבר אנושי על כל 24 השאלות — לוודא grounding אמיתי (Gemini לפעמים "מוסיף" פרט לא בקטע); לתקן/לדגום מחדש במקרה כזה.

### 6 שאלות קשות בכתב יד (`difficulty=hard`)

מבוססות על תוכן שנקרא בפועל (employees, self-employed, real-estate, general guides):

1. **Multi-hop #1** (employees + self-employed): "האם מדרגות מס ההכנסה לעצמאים זהות לאלה של שכירים, ומהו ההבדל בשיעורי ביטוח לאומי בין השניים?" — מדרגות זהות (מאושר: self-employed guide §1 אומר "זהות למדרגות שכיר"); ביטוח לאומי לעצמאי 7.7%/18% (מאושר ישירות מ-btl.gov.il, self-employed guide §2) — יש להשוות מול השיעור המדויק לשכיר ב-`employees-tax-guide.md` (לא נקרא כרגע בשלמותו — לקרוא לפני הקפאה סופית של ה-reference answer).
2. **Multi-hop #2** (capital-markets + real-estate): "האם שיעור המס על רווח הון ממכירת מניות זהה לשיעור מס השבח על מכירת דירה?" — capital-markets §1: 25% רווח הון ריאלי מניירות ערך; real-estate §1: עד 25% מס שבח על השבח הריאלי (סעיף 48א(ב1)(1)). התשובה ("כן, שניהם עד 25%, אך בסיסי החישוב והפטורים שונים") **מחייבת** את שני המסמכים.
   > **תיקון לעומת הטיוטה**: הניסוח המקורי (תקרת מס יסף כללית מול מכירת דירה) **נפסל באימות** — [employees-tax-guide.md:166-172](../../../c:/Repo/Taxes/TaxData/employees/employees-tax-guide.md) מכיל גם את 721,560 ₪ וגם את 5,385,285 ₪ באותו סעיף, כלומר צ'אנק **אחד** עונה על הכול. זו בדיוק "מלכודת הצ'אנק היחיד" שהמטלה מזהירה מפניה.
3. **Unanswerable #1**: "מהו שיעור מס החברות שחל על חברה בע\"מ בישראל בשנת 2026?" — `answerable=False`. **הערת אימות**: [capital-markets-tax-guide.md:129](../../../c:/Repo/Taxes/TaxData/capital-markets/capital-markets-tax-guide.md) מזכיר "מס חברות (סעיפים 121 או 126 לפקודה)" בהקשר קריפטו, אך **לעולם לא נוקב בשיעור**. זהו near-miss מכוון ומתועד: retrieval יאחזר צ'אנק לכאורה-רלוונטי, והמערכת חייבת בכל זאת לסרב. אם בפועל זה מתברר כעמום מדי לשופט — חלופה נקייה לגמרי (0 נוכחות בקורפוס): "מהו שיעור המכס על יבוא מוצרי אלקטרוניקה לישראל?".
4. **Unanswerable #2**: "האם קיימת הטבת מס ייעודית לרכישת רכב חשמלי בישראל, ומה שיעורה?" — `answerable=False`. **הערת אימות**: המילה "רכב" מופיעה פעם אחת ב-`self-employed-tax-guide.md:79` כדוגמה לקטגוריית הוצאה מוכרת — מלכודת לקסיקלית מכוונת, שימושית במיוחד לניסוי ה-BM25 (BM25 יאחזר את הצ'אנק הזה; המערכת חייבת עדיין לסרב).
5. **Negation**: "האם בעל דירת מגורים נוספת (שאינה יחידה) זכאי לאותו פטור/מדרגת-0% ממס רכישה שניתן לרוכש דירה יחידה?" — **לא**: מאומת ישירות — real-estate guide §3.1 (דירה יחידה: 0% עד 1,978,745 ₪) מול §3.2 (דירה נוספת: 8% מהשקל הראשון, הוראת שעה). ניגוד מפורש וברור.
6. **Exact identifier**: "לפי איזה סעיף בחוק מיסוי מקרקעין נקבעת **תקרת השווי** לפטור ממס שבח לדירת מגורים יחידה?" — **תיקון לעומת טיוטת ה-Plan agent**: קריאה מלאה של real-estate guide §2 מראה ש-49א(א1) הוא הסעיף שקובע את **תקרת** הפטור (5,008,000 ₪), בעוד שהפטור עצמו מוסדר בסעיף 49ב. ניסחתי את השאלה מחדש כך שהיא שואלת ספציפית על התקרה — כך ש-49א(א1) הוא Reference Answer מדויק ולא עמום.

> **סטטוס אימות**: כל 5 מדריכי ה-md נקראו במלואם ותוכן השאלות אומת מולם. שאלה #1 מאומתת סופית: שכיר 4.27%/12.17% (`employees-tax-guide.md` §4) מול עצמאי 7.7%/18% (`self-employed-tax-guide.md` §2), מדרגות מס זהות (מוצהר מפורשות בשני המסמכים). **אזהרה**: `employees-tax-guide.md:119` מכיל הערת אי-עקביות מפורשת על 5.55%/14.6% מול 4.27%/12.17% — ה-`reference_answer` חייב לנקוב ב-4.27%/12.17% (הניכוי בפועל מהעובד) ולא להיגרר לספרות ה"מזה".

## 3. `build_index.py` (Task 3) — `tax-copilot/src/build_index.py`

- **Embeddings**: מחלקה עצמאית `tax-copilot/src/bge_embeddings.py` (לא wrapper מספרייה) — `embed_documents()` בלי prefix, `embed_query()` עם prefix `"Represent this sentence for searching relevant passages: "`. `normalize_embeddings=True` (bge מאומן ל-cosine; FAISS `IndexFlatL2` על וקטורים מנורמלים מדרג נכון).
- **Parse**: `TextLoader` ל-md (מסמך שלם אחד), `PyPDFLoader` ל-PDF (עמוד = מסמך אחד, `metadata["page"]` אוטומטי).
- **Chunk**: `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150, add_start_index=True)` — **לא לכוונן** בשלב זה (Task 6 בלבד).
- **Enrich**: לכל צ'אנק — `doc_name, doc_format, page, section, language="he", source_url, start_index`. עבור md: `section` נגזר מהכותרת (`#`/`##`/`###`) הקרובה ביותר לפני `start_index` (regex `^#{1,3}\s+(.+)$` על הטקסט הגולמי, bisect לפי היסט).
- **Store**: `FAISS.from_documents(chunks, embeddings)`, `vs.save_local("tax-copilot/assignment3/index")` — **מחויב לגיט** (החלטה §0).
- **"תראה בעיניים" (חובה, לא אופציונלי)**: להדפיס 10 צ'אנקים אקראיים (`random.sample`) + 3 שאילתות sanity דרך `similarity_search` (למשל: "מהו שיעור מס היסף?" — מופיע ב-3 מסמכים שונים, בודק איזה חוזר; "כמה עמודים מוקדשים לטופס 106 בלוח העזר?" — ממוקד ב-PDF). לתעד בכתב את הממצאים (עברית/RTL תקין? צ'אנקים חתוכים? הצ'אנק הנכון חזר?) ב-write-up **אחרי** שרואים את הפלט בפועל, לא לפני.

### ⚠️ שער go/no-go — bge-small-en על קורפוס עברי

`BAAI/bge-small-en-v1.5` הוא מודל **אנגלית בלבד** עם tokenizer WordPiece אנגלי. הקורפוס וכל 30 השאלות בעברית. קיים סיכון ממשי שה-retrieval יהיה קרוב לאקראי — ואז Task 5 מתנוון ל"הכול נכשל" ואי אפשר להפיק ממנו את ניתוחי (a)/(b)/(c) שהמטלה דורשת.

**הגייט**: אחרי הרצת 3 שאילתות ה-sanity בשלב זה, להעריך אם הצ'אנק הנכון חוזר ולו חלקית.
- **אם ה-retrieval סביר** — ממשיכים כמתוכנן: bge-small-en נשאר ה-baseline, וההחלפה למודל רב-לשוני היא ניסוי 1 ב-Task 6.
- **אם ה-retrieval קטסטרופלי** — **זה עצמו ממצא Task 3 מהמעלה הראשונה** ויש לתעד אותו ככזה. אז הופכים את הסדר: `intfloat/multilingual-e5-small` הופך ל-baseline התפעולי, ו-bge-small-en נשמר כ"ניסוי בכיוון ההפוך" שמתעד את הכשל. זו קריאה כנה ומוצדקת של המטלה — לא עקיפה שלה.

לקבל את ההחלטה **לפני** שמריצים Task 4/5, לא אחרי שנשרפו ~200 קריאות.

## 4. RAG pipeline (Task 4) — `tax-copilot/src/rag_pipeline.py`

```python
class GroundedAnswer(BaseModel):
    answer: str
    sources: list[str]   # "doc_name, section/page N" לכל צ'אנק שצוטט
    evidence: list[str]  # השורות המצוטטות המדויקות
    answered: bool

REFUSAL_SENTENCE = "לא מצאתי את זה במסמכים המצורפים."

def answer_with_rag(query: str, k: int = 5, vectorstore=None) -> GroundedAnswer: ...
```

פרומפט: צ'אנקים ממוספרים `[1]`, `[2]`... עם מפריד ברור (`---`) ומטא-דאטה מוצגת (`מסמך: X | סעיף/עמוד: Y`) לפני כל צ'אנק. system prompt: לענות רק מהקונטקסט הממוספר, לצטט `[n]` לכל טענה, להשיב במשפט הסירוב המדויק אם לא נמצא, להחזיר JSON תקני בלבד (Pydantic schema) — לקלף fences הגנתית לפי מוסכמת הפרויקט.

**Guard דטרמיניסטי לציטוטים** (0 קריאות LLM) — עוטף את `answer_with_rag`, לא בתוך ה-schema עצמו (השאר את החתימה `answer_with_rag(query, k=5)` בדיוק כפי שהמטלה מגדירה):
```python
def answer_with_rag_instrumented(query, k=5, vectorstore=None) -> tuple[GroundedAnswer, dict]:
    # מודד latency/tokens, בודק cited_numbers מול טווח 1..k בפועל,
    # מסמן citation_flag אם צוטט מספר מחוץ לטווח, כותב log
```
`assignment3_run_rag.py` (Task 4 runner על כל ה-eval set) קורא ל-`answer_with_rag_instrumented`.

**Cross-check ל-`answered`**: השדה מגיע מה-LLM ולכן לא אמין כשלעצמו — המודל עלול להחזיר `answered=True` יחד עם משפט הסירוב. בקוד: אם `REFUSAL_SENTENCE` מופיע ב-`answer`, לכפות `answered=False` ולתעד את אי-ההתאמה (אותו רוח כמו ה-citation guard — בדיקה דטרמיניסטית במקום אמון בפלט).

**Sanity check לפני הרצה מלאה**: להריץ את 2 השאלות ה-unanswerable דרך `answer_with_rag`, לוודא `answered=False` ו-`answer == REFUSAL_SENTENCE`. אם לא — לחזק את system prompt לפני הרצה על 30 שאלות.

> כל הסקריפטים החדשים שקוראים ל-Gemini עוקבים אחרי `tax-copilot/.claude/skills/add-llm-script/SKILL.md` (client setup, `sys.stdout.reconfigure`, קילוף fences, throttle/retry) — לא לגזור מחדש את הדפוס.

## 5. Task 1 — baseline — `tax-copilot/src/assignment3_baseline.py`

`ask_baseline(question)` — אותה צורת `ask()` throttled כמו `assignment2_generate.ask()`, **בלי מסמך בפרומפט כלל**. system prompt: "ענה רק אם אתה בטוח מידע כללי; אם לא — 'אינני יודע.'".

סיווג (`refused`/`answered correctly`/`hallucinated`) משתמש ב-`judges.judge_correctness()` המשותף (§6) — לא לשכפל לוגיקת שיפוט:
```python
def classify_baseline(question, generated_answer, reference_answer, answerable) -> str:
    if generated_answer.strip() == "אינני יודע.": return "refused"
    verdict = judge_correctness(question, generated_answer, reference_answer).verdict
    return "correct" if verdict == "good" else "hallucinated"
```
פלט: `assignment3/data/baseline_results.csv`.

## 6. Task 5 — evaluation — `tax-copilot/src/assignment3_evaluate.py` + מודולים משותפים

### מודולים משותפים (גם ל-Task 6)

`retrieval_eval.py` — `hit_rate_row()`: פיצול `evidence_doc`/`evidence_page` לפי `;` (multi-hop), בודק אם צ'אנקים שאוחזרו כוללים את `doc_name` הנדרש. מחזיר **שני** מדדים: `hit_at_k` (כל המסמכים הנדרשים אוחזרו — הקריטריון למולטי-הופ) ו-`hit_at_k_any_doc` (לפחות אחד). ההתאמה הראשית היא ברמת `doc_name`; `page`/`section` נרשמים כבדיקת בונוס בלבד, כי מחרוזות כותרת עלולות להשתנות קלות בין ה-CSV לבין ה-metadata בפועל. מדלג על שורות `answerable=False`.

`judges.py` (מבנה זהה ל-`assignment2_judge.py`: אותו client, `JUDGE_MODEL="gemini-3.1-flash-lite"`, אותו throttle/retry/fence-strip, `explanation` לפני `verdict`, `Literal["good","ok","bad"]`):
- `judge_context_relevance(question, chunks)` — **רק** שאלה+צ'אנקים, בלי התשובה (שלא "יחשוב אחורה" מהתשובה)
- `judge_faithfulness(answer, chunks)` — **רק** תשובה+צ'אנקים, בלי reference
- `judge_answer_relevance(question, answer)` — רק שאלה+תשובה
- `judge_correctness(question, answer, reference_answer)` — +reference

כל אחד פונקציה נפרדת עם רוברייק/פרומפט משלה — כך ש"faithfulness לא רואה reference" הוא עובדה מבנית, לא משמעת שצריך לזכור.

`refusal_correctness.py`: `correct_refusal` / `false_answer` (מסוכן) / `false_refusal` / `correct_answer`.

### הרכבה

`assignment3_evaluate.py` מאחד eval-set + baseline_results.csv + rag_results.csv (מ-Task 4 runner, כולל metadata של הצ'אנקים שאוחזרו) → לכל שורה: hit@k (RAG בלבד), 4 judges על RAG, 2 judges רלוונטיים על baseline (`answer_relevance`, `correctness` — `context_relevance`/`faithfulness`="N/A", אין צ'אנקים ל-baseline), refusal-correctness לשני המערכות בנפרד.

פלט `assignment_03.xlsx` — כל העמודות שהמטלה דורשת (§ "What to submit") + sheet שני `summary_table`: `groupby("difficulty")`, ממוצע ציונים (good=1/ok=0.5/bad=0), hit@k, ספירת refusal-correctness, latency/tokens ממוצעים — זו טבלת easy/hard הנדרשת.

### (a)/(b)/(c)

פונקציות עזר שמאתרות מועמדים (לא כותבות את הניתוח אוטומטית — הניתוח עצמו הוא קריאה אנושית של הצ'אנקים בפועל, כפי שהמטלה דורשת במפורש):
- `find_rag_worse_than_baseline` — baseline נכון, RAG correctness ok/bad
- `find_right_answer_broken_pipeline` — RAG correctness=good אבל hit@k=False
- `worst_5_rag_rows` — ציון ממוצע נמוך ביותר על 4 הקריטריונים; לסווג כל אחת retrieval-failure (hit@k כשל) מול generation-failure (hit@k הצליח אבל faithfulness/correctness כשל) — תוך הדבקת הצ'אנקים המלאים ב-write-up כראיה.

## 7. Task 6 — שלושה ניסויי שיפור — `tax-copilot/src/assignment3_experiments.py`

> **כמה ניסויים? שלושה.** `assignment3.md` סותר את עצמו: [שורה 258](../../../c:/Repo/Taxes/HomeWork/assignment3.md) אומרת "Run **two** experiments", אבל שורה 22 (סיכום הקשת), שורה 282 (צ'קליסט "Done when") ושורה 314 (רשימת ההגשה) כולן אומרות **three**. 3 מול 1 — הולכים על שלושה. עלות: +150 קריאות (~10 דק').

### שלב א — sweeps חינמיים (0 קריאות LLM, hit-rate בלבד)

`sweep_top_k`, `sweep_chunk_size`, `sweep_embedding_model`, `sweep_hybrid_bm25` — כולם משתמשים ב-`retrieval_eval.hit_rate_row`. פלט: `assignment3/data/task6_sweeps.csv`. מריצים את כל ה-sweeps **לפני** התחייבות לניסויים המלאים, בדיוק כמו שהמטלה ממליצה. אינדקסים זמניים שנבנים ב-sweeps נכתבים ל-temp ו**לא** מחויבים לגיט (רק `assignment3/index/` הראשי מחויב).

### שלב ב — שלושת הניסויים המלאים (עם judges)

**ניסוי 1 — מודל embedding רב-לשוני** (מאושר §0): השערה — bge-small-en הוא אנגלית-בלבד, הקורפוס וכל 30 השאלות בעברית, ולכן hit-rate נפגע באופן רוחבי (לא רק בקשות); מעבר ל-`intfloat/multilingual-e5-small` (דורש מחלקת `Embeddings` שנייה עם prefix `"query: "`/`"passage: "`) אמור לשפר משמעותית בלי לשנות משתנה אחר (אותו chunk_size, אותו k=5). מדידה מלאה מחדש על אותן 30 שאלות, כ-delta מ-Task 5.

**ניסוי 2 — hybrid dense+BM25**: השערה — שאלת ה-identifier (`49א(א1)`) נכשלת ב-hit-rate תחת dense retrieval טהור כי bge לא שומר טוקנים מדויקים; `EnsembleRetriever` (dense + BM25, משקלים [0.5,0.5]) על **אותו** אינדקס bge-small-en המקורי אמור לתקן שורה זו ספציפית בלי לפגוע באחרות. נמדד בנפרד מול Task 5 (לא בשילוב עם ניסוי 1 — "משתנה אחד בכל פעם"). **הערת מימוש**: `rank_bm25` מפצל ברווחים כברירת מחדל — לוודא ש-`49א(א1)` שורד כטוקן; אם לא, לכוונן tokenizer ולתעד זאת כחלק מהניסוי.

**ניסוי 3 — נבחר לפי תוצאות שלב א'.** מועמד ברירת מחדל: `top-K` (5→8) אם ה-sweep מראה שהצ'אנק הנכון קיים אך מדורג מתחת ל-5; חלופה: `chunk_size` אם ה-sweep מראה שתשובות נחתכות בגבולות צ'אנק; חלופה שלישית: prompt generation אם Task 5 מראה שהכשל הוא generation ולא retrieval (ספירת (c)). **ההחלטה מתקבלת אחרי שלב א' ו-Task 5, ונרשמת כהשערה pre-registered לפני ההרצה** — לא לבחור בדיעבד לפי מה שיצא יפה.

פלט: `assignment3/assignment3_experiments.xlsx` עם sheets: `sweeps`, `exp1_multilingual_embeddings`, `exp2_hybrid_bm25`, `exp3_<tbd>`, `delta_summary`, `experiment_log` (השערה/שינוי/מסקנה — כמו `assignment2_experiments.py`).

**אזהרת רעש לכתוב ב-write-up**: 6 שאלות קשות = ~16.7 נק' אחוז לכל שאלה — יותר מסף ה-3.3% שהמטלה עצמה מזהירה מפניו על 30 שאלות. לא לתבוע שיפור מ-1-2 שורות שהתהפכו.

## 8. מבנה תיקיות סופי

```
Taxes/
├── TaxData/employees/income-tax-deductions-booklet-2026.pdf   (חדש)
└── tax-copilot/
    ├── requirements.txt   # + langchain, langchain-community, langchain-huggingface,
    │                      #   sentence-transformers, faiss-cpu, pypdf, rank_bm25
    ├── src/
    │   ├── build_index.py
    │   ├── bge_embeddings.py
    │   ├── rag_pipeline.py
    │   ├── assignment3_generate_eval.py
    │   ├── assignment3_baseline.py
    │   ├── assignment3_run_rag.py
    │   ├── retrieval_eval.py
    │   ├── judges.py
    │   ├── refusal_correctness.py
    │   ├── assignment3_evaluate.py
    │   └── assignment3_experiments.py
    └── assignment3/
        ├── data/ (corpus_manifest.json, tax_rag_eval_set.csv, baseline_results.csv, rag_results.csv, task6_sweeps.csv)
        ├── index/                        # FAISS — מחויב לגיט
        ├── assignment_03.xlsx
        ├── assignment3_experiments.xlsx
        └── assignment3_writeup.md
```

## 9. סדר ביצוע

1. הורדת ה-PDF ל-`TaxData/employees/`; כתיבת `corpus_manifest.json`.
2. `pip install` תלויות חדשות + עדכון `requirements.txt`.
3. `bge_embeddings.py` → `build_index.py`; הרצה; קריאת פלט 10 הצ'אנקים + 3 השאילתות; **הכרעת שער ה-go/no-go של §3**; כתיבת ממצאי Task 3.
4. ניסוח סופי ל-6 השאלות הקשות (התוכן כבר אומת מול המקורות — נשאר רק לנסח ולוודא התאמת מחרוזות `evidence_page` לכותרות בפועל).
5. `assignment3_generate_eval.py` ל-24 השאלות הסינתטיות; מעבר אנושי; הרכבת `tax_rag_eval_set.csv` השלם (30 שאלות).
6. `rag_pipeline.py`; sanity check על 2 השאלות הבלתי-ניתנות-למענה.
7. `assignment3_baseline.py` — הרצה על 30 שאלות.
8. `assignment3_run_rag.py` — הרצה על 30 שאלות.
9. `retrieval_eval.py`, `judges.py`, `refusal_correctness.py`, `assignment3_evaluate.py` — הרצת Task 5; כתיבת הטבלה + (a)/(b)/(c) מהפלט בפועל.
10. `assignment3_experiments.py` — שלב א' (sweeps חינמיים) קודם, ואז שני הניסויים המלאים.
11. `assignment3_writeup.md` — מבוסס על התוצרים שכבר קיימים, לא חישוב מחדש.
12. Commit קוד + קורפוס + eval set + xlsx + write-up (מכבד `.gitignore` הקיים — `HomeWork/`/`plans/` נשארים מחוץ).

## 10. תקציב קריאות LLM (הכל lite-tier, 15 req/min, `sleep(4)` בין קריאות, retry 5×/`sleep(15)`)

| שלב | קריאות | הערה |
|---|---|---|
| Task 2 (יצירת שאלות סינתטיות) | ~24 | |
| Task 1 (baseline) | 30 | + עד 30 `judge_correctness` לסיווג (לא לספור כפול עם Task 5) |
| Task 4 (RAG generation, כל ה-eval set) | 30 | |
| Task 5 (RAG judges) | 120 | 4×30 |
| Task 5 (baseline judges) | 60 | 2×30 |
| Task 6 שלב א (sweeps) | 0 | retrieval בלבד |
| Task 6 ניסוי 1 | 150 | 30 gen + 120 judge |
| Task 6 ניסוי 2 | 150 | 30 gen + 120 judge |
| Task 6 ניסוי 3 | 150 | 30 gen + 120 judge |
| **סה"כ** | **~690–714** | ~50–55 דק' ריצה, כולה lite-tier — לא נוגעת בתקרת 20/יום של הטייר הרגיל |

התלויות שיתווספו ל-`requirements.txt` (אומת — אף אחת מהן לא מותקנת כרגע): `langchain`, `langchain-community`, `langchain-huggingface`, `sentence-transformers`, `faiss-cpu`, `pypdf`, `rank_bm25`. `torch` ו-`transformers` **כבר** קיימים, כך ש-`sentence-transformers` יעלה על תשתית קיימת.

## 11. אימות מקצה לקצה

- `python src/build_index.py` — לוודא שנוצר index תקין ב-`assignment3/index/`, לקרוא את הפלט של 10 הצ'אנקים/3 השאילתות בעין.
- להריץ את `answer_with_rag` ידנית על שתי השאלות הבלתי-ניתנות-למענה ולוודא refusal.
- להריץ את כל 5 הסקריפטים (baseline → run_rag → evaluate → experiments) ולוודא ש-`assignment_03.xlsx` ו-`assignment3_experiments.xlsx` נפתחים ומכילים את כל העמודות הנדרשות ללא ערכים ריקים לא-מוסברים.
- לבדוק ידנית 3-4 שורות מ-`assignment_03.xlsx` מול הצ'אנקים בפועל — לוודא שהציטוטים וה-hit@k הגיוניים לפני כתיבת ה-write-up.
