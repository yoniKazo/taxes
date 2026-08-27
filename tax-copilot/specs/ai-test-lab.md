# Spec: AI Test Lab (`api/` — agents, rubric, runs, ratings, judge, agreement)

## תיאור
כלי הערכת-איכות פנימי ל-agents מבוססי-LLM של Tax Copilot, בנוי כ-web layer (FastAPI + SQLite) מעל אותה מתודולוגיה שכבר יושמה ידנית במטלה 2 (רוברייק, דאטהסט, generation, ניקוד אנושי, LLM-judge, ניתוח agreement) — הפעם דרך UI ולא סקריפטים/xlsx. ה-Test Lab בגרסה הזו בודק את agent ה-`qa` מול דאטהסט `tax_qa_v1` (24 שאלות), כי זהו ה-agent שתואם לדאטהסט הקיים מבחינת סוג שאלה. בדיקת `explainer` באותו מנגנון היא הרחבה עתידית, לא כלולה כאן.

## קלט
| שם | סוג | חובה/ברירת מחדל |
|---|---|---|
| `agent_name` (ל-`POST /test-runs`) | `"explainer"` \| `"qa"` \| `"judge"` | חובה |
| `model`, `temperature`, `system_prompt` (ל-`POST /test-runs`) | override אופציונלי מעל ברירות המחדל של ה-agent | ברירת מחדל: `None` → נופל לברירת המחדל של ה-agent מה-DB |
| `question_ids` (ל-`POST /test-runs`) | רשימת מזהי `test_questions` | חובה |
| `model` (ל-`POST /test-runs/{id}/judge`) | override אופציונלי מעל ברירת המחדל של agent ה-judge | ברירת מחדל: `None` → נופל לברירת המחדל של ה-agent מה-DB |
| `scores` (ל-`POST /llm-calls/{id}/ratings`) | `dict[criterion, "good"\|"ok"\|"bad"]` | חובה, `rater="human"` בלבד |

## Acceptance criteria (EARS)

1. **Ubiquitous** — כל קריאת LLM (הן מ-`/calculate` והן מה-Test Lab) תישמר כשורה בטבלת `llm_calls`, כולל agent, מודל, טמפרטורה, פרומפט מערכת, שאלה/הקשר, תשובה, latency ו-tokens.
2. **Event-driven (WHEN)** — כאשר מופעל `POST /test-runs` עם `agent_name` ורשימת `question_ids`, המערכת תריץ את ה-agent הנבחר על כל שאלה בנפרד (throttled, לפי `.claude/rules/hosted-llm-quota.md`) ותשמור תוצאה פר-שאלה כשורת `llm_calls` נפרדת עם `source='test'` ו-`test_run_id` מקושר.
3. **Event-driven (WHEN)** — כאשר מוגש ניקוד אנושי (`POST /llm-calls/{id}/ratings`), המערכת תחשב ותשמור `final_score` (`pass`/`fail`) לפי ה-pass-bar וה-go/no-go rules של הרוברייק המקושרת ל-`test_run` (`test_runs.rubric_id`) — לא בהכרח הרוברייק הפעילה-כרגע אם היא כבר השתנתה מאז ההרצה.
4. **Event-driven (WHEN)** — כאשר מופעל `POST /test-runs/{id}/judge`, המערכת תריץ את ה-agent `judge` על כל תוצאה בריצה שעדיין אין לה ניקוד `judge`, ותשמור `verdict`+`explanation` פר-קריטריון וכן `final_score` מחושב, על `llm_call_id` של התשובה הנשפטת (לא של קריאת ה-judge עצמה). ריצה חוזרת על תוצאות שכבר נשפטו מדלגת עליהן (idempotent).
5. **Ubiquitous** — קריטריון Latency לעולם לא נשלח ל-judge; הוא מדורג תכנותית מתוך `latency_ms` הקיים באותו llm_call (good ≤2000ms, ok ≤5000ms, אחרת bad), בדיוק כמו ב-`assignment2_judge.py`.
6. **Unwanted behavior (IF/THEN)** — אם קריאת LLM נכשלת בזמן ריצת `/test-runs` (rate limit וכו'), השגיאה תירשם ב-`llm_calls.error` עבור אותה שורה בלבד; שאר השאלות בבאצ' ימשיכו לרוץ ולא תיפול כל הריצה.
7. **State-driven (WHILE)** — כל עוד קיים גם ניקוד `human` וגם ניקוד `judge` לאותו `llm_call_id`+קריטריון, `GET /test-runs/{id}/agreement` יכלול את הזוג הזה בחישוב אחוז ה-agreement (ולא יכלול llm_calls שיש להם רק rater אחד).

## Out of scope
- Multi-tenant / authentication.
- עריכה רטרואקטיבית של agreement rate היסטורי.
- תמיכה בכמה datasets פעילים בו-זמנית ב-UI (v1 עובד על dataset אחד פעיל, `tax_qa_v1`).
- בדיקת agent `explainer` באותו מנגנון (דורש דאטהסט מסוג תרחישי-חישוב, לא נבנה כאן — התשתית תומכת בזה כש-`agent_name` גנרי בכל מקום).
- הוספת/עריכת agents דרך ה-UI (`POST /agents`) — שלושת ה-agents קבועים דרך seed/קוד בלבד ב-v1.
- override של טמפרטורה/פרומפט לקריאת ה-`judge` עצמה דרך `/test-runs/{id}/judge` — קבועים לברירת המחדל של ה-agent. **מודל** כן ניתן ל-override (`JudgeRunRequest.model`, אותה סמנטיקת `None` → נופל לברירת המחדל), כדי לאפשר לבחור בין Gemini ל-Anthropic Claude Haiku גם עבור ה-judge, לא רק עבור ה-writer.

## הערות עיצוב (הפניה למקור)
- גרסאות רוברייק: `PUT /rubrics/active` יוצר שורת `rubrics` חדשה (ולא עורך קיימת), כדי ש-`test_runs.rubric_id` הישנים ימשיכו להצביע על הרוברייק שבאמת הייתה בשימוש בזמן ההרצה. ראו `api/db/schema.sql`.
- `ratings.llm_call_id` מצביע תמיד על התשובה הנשפטת (שורת ה-`qa`/`explainer`), אף פעם לא על שורת `llm_calls` של קריאת ה-judge עצמה.
- UNIQUE constraint על `ratings(llm_call_id, rater, criterion)` מאפשר upsert (מחיקה+הכנסה מחדש) — תיקון ניקוד לא יוצר כפילויות ולא משבש את חישוב ה-agreement.
