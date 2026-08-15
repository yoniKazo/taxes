CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,              -- 'explainer' | 'qa' | 'judge'
    description TEXT,
    default_model TEXT NOT NULL,
    default_system_prompt TEXT NOT NULL,
    default_temperature REAL NOT NULL DEFAULT 0.7
);

-- גרסאות רוברייק: PUT /rubrics/active לא עורך שורה קיימת (זה היה משנה רטרואקטיבית
-- את הרוברייק שכבר יוחסה ל-test_runs ישנים) -- הוא יוצר שורה חדשה + criteria חדשים
-- ומעביר is_active=1 אליה, כבה את הישנה. test_runs.rubric_id ממשיך להצביע על הגרסה
-- שבאמת הייתה בשימוש בזמן הריצה.
CREATE TABLE IF NOT EXISTS rubrics (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0,   -- בדיוק שורה אחת עם 1 בכל רגע נתון
    pass_bar_min_good INTEGER NOT NULL,     -- 4, כמו מטלה 2
    pass_bar_max_bad INTEGER NOT NULL,      -- 0
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rubric_go_no_go (
    id INTEGER PRIMARY KEY,
    rubric_id INTEGER NOT NULL REFERENCES rubrics(id),
    criterion TEXT NOT NULL,                -- 'Grounding' | 'Length' | ...
    fails_unless_good INTEGER NOT NULL DEFAULT 0,  -- 1: קריטריון בטיחות (כמו Grounding)
    fails_if_bad INTEGER NOT NULL DEFAULT 0         -- 1: דוחה אוטומטית אם bad (כמו Length)
);

CREATE TABLE IF NOT EXISTS rubric_criteria (
    id INTEGER PRIMARY KEY,
    rubric_id INTEGER NOT NULL REFERENCES rubrics(id),
    name TEXT NOT NULL,                     -- Fluency/Grammar/Tone/Length/Grounding/Latency
    good_def TEXT NOT NULL,
    ok_def TEXT NOT NULL,
    bad_def TEXT NOT NULL,
    is_programmatic INTEGER NOT NULL DEFAULT 0,  -- 1 = Latency: מדורג בקוד, לא נשלח ל-judge
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS test_questions (
    id INTEGER PRIMARY KEY,
    dataset_name TEXT NOT NULL,             -- 'tax_qa_v1'
    category TEXT,                          -- יש-במסמך / לא-קיים-כלל / מתחכמת
    question_text TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS test_runs (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    rubric_id INTEGER NOT NULL REFERENCES rubrics(id),  -- גרסת הרוברייק שהייתה active בזמן ההרצה, קפואה
    model TEXT NOT NULL,
    temperature REAL NOT NULL,
    system_prompt TEXT NOT NULL,
    label TEXT                              -- הערת ניסוי, למשל "בלי בולרפלייט" -- ממולא מ-RunForm
);

-- llm_calls.question מכיל את השאלה/הקשר בפועל שנשלח (למשל שאלת ה-qa, או מחרוזת
-- ההקשר שנבנתה עבור explainer) -- *לא* את תוכן data/tax_notes.md המלא. המסמך עצמו
-- לא משוכפל בכל שורה: הוא נטען מחדש מהקובץ בזמן קריאה (הוא סטטי וכבר קיים בריפו).
-- שורת llm_calls נוצרת גם עבור קריאת ה-judge עצמה (agent_name='judge') -- ראו
-- הבהרה תחת ratings למטה על ההבדל בין "הקריאה שנשפטת" ל"קריאת ה-judge עצמה".
CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    model TEXT NOT NULL,
    temperature REAL NOT NULL,
    system_prompt TEXT NOT NULL,
    question TEXT NOT NULL,
    response TEXT,
    latency_ms REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    source TEXT NOT NULL,                   -- 'live' | 'test'
    test_run_id INTEGER REFERENCES test_runs(id),
    error TEXT
);

-- ratings.llm_call_id מצביע תמיד על *התשובה שנשפטת* (שורת ה-qa/explainer),
-- אף פעם לא על שורת llm_calls של קריאת ה-judge עצמה -- ראו הבהרה בסעיף 4.
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY,
    llm_call_id INTEGER NOT NULL REFERENCES llm_calls(id),
    rater TEXT NOT NULL,                    -- 'human' | 'judge'
    criterion TEXT,                         -- NULL = שורת final_score כוללת
    verdict TEXT,                           -- good/ok/bad, או pass/fail בשורת ה-NULL
    explanation TEXT,                       -- הנמקת judge; NULL אצל human
    created_at TEXT NOT NULL,
    UNIQUE(llm_call_id, rater, criterion)   -- מאפשר upsert: ניקוד חוזר מחליף, לא משכפל
);
