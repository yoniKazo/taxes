"""Idempotent seed data: agents, rubric (verbatim from assignment2_rubric.md), and
the 24-question tax_qa_v1 dataset (verbatim from assignment2/data/tax_qa_dataset.md).
Only inserts into a table if it is currently empty -- safe to call on every app startup.
"""

import sqlite3
from datetime import datetime, timezone

AGENTS = [
    {
        "name": "explainer",
        "description": "מסביר תוצאת חישוב מס ספציפית בעברית פשוטה",
        "default_model": "gemini-flash-lite-latest",
        "default_system_prompt": (
            "אתה יועץ מס ידידותי ומדויק. תפקידך להסביר למשתמש בעברית פשוטה וברורה "
            "את תוצאת חישוב המס שלו, בהתבסס אך ורק על המספרים שסופקו לך -- אל תמציא "
            "נתונים, אל תוסיף הנחות שלא נמסרו. הסבר קצר, ידידותי ומדויק, בלי ז'רגון "
            "מיותר."
        ),
        "default_temperature": 0.7,
    },
    {
        "name": "qa",
        "description": "בוט שאלות-תשובות מבוסס-מקור על data/tax_notes.md",
        "default_model": "gemini-flash-lite-latest",
        "default_system_prompt": (
            "ענה אך ורק לפי המסמך המצורף. אל תשתמש בידע חיצוני ואל תנחש.\n"
            "כאשר אתה עונה, צטט את הקטע המדויק מהמסמך שתומך בתשובה.\n"
            'אם התשובה אינה מופיעה במסמך, השב אך ורק במשפט: "לא מצאתי את זה במסמך."'
        ),
        "default_temperature": 0.7,
    },
    {
        "name": "judge",
        "description": "LLM-as-judge -- מיישם רוברייק, מחזיר verdict+explanation לכל קריטריון",
        "default_model": "gemini-3.1-flash-lite",
        "default_system_prompt": (
            "אתה שופט איכות (LLM judge). פרומפט המערכת בפועל נבנה דינמית בזמן קריאה "
            "מתוך rubric_criteria -- זהו placeholder בלבד."
        ),
        "default_temperature": 0,
    },
]

# Copied verbatim from assignment2/assignment2_rubric.md ("1a. הגדרות דירוג לכל קריטריון").
RUBRIC_CRITERIA = [
    {
        "name": "Fluency",
        "good_def": "התשובה קריאה כמשפט/משפטים טבעיים בעברית; אין ניסוח מוזר או מבנה שבור.",
        "ok_def": "1–2 ניסוחים מגושמים או לא-אידיומטיים, אך המשמעות ברורה בקריאה ראשונה.",
        "bad_def": "3+ ניסוחים מגושמים, או משפט שצריך לקרוא פעמיים כדי להבין, או ערבוב שפות/תווים לא תקין.",
        "is_programmatic": 0,
    },
    {
        "name": "Grammar",
        "good_def": "אין שגיאות כתיב/פיסוק/התאמת מין-מספר.",
        "ok_def": "1–2 שגיאות קטנות (כתיב/פיסוק) שלא פוגעות בהבנה.",
        "bad_def": "3+ שגיאות, או שגיאה שמשנה את המשמעות (למשל התאמת מין/מספר שהופכת משפט חיובי לשלילי).",
        "is_programmatic": 0,
    },
    {
        "name": "Tone",
        "good_def": 'קול יועץ מס ידידותי, בטוח ומדויק — לא יבש-רובוטי ולא "משווק" מדי; פונה למשתמש בכבוד ובבהירות.',
        "ok_def": "הטון סביר אך שטוח/גנרי (למשל תשובה יבשה מדי, או חסרת חום), בלי לפגוע במקצועיות.",
        "bad_def": 'טון לא מתאים: מתנשא, מתחמק, אגרסיבי, "משפטי" מדי (disclaimer-heavy עד כדי חוסר שימושיות), או סתם קופי-פייסט של קטע מהמסמך בלי ניסוח.',
        "is_programmatic": 0,
    },
    {
        "name": "Length",
        "good_def": '1–3 משפטים ממוקדים (או משפט קצר יחיד כשזו התשובה המלאה, כולל "לא מצאתי את זה במסמך").',
        "ok_def": "4–5 משפטים, או משפט יחיד לא-שלם/קטוע.",
        "bad_def": "6+ משפטים (פירוט-יתר/רשימה ארוכה), או תשובה ריקה/מילה בודדת שאינה תשובה.",
        "is_programmatic": 0,
    },
    {
        "name": "Grounding",
        "good_def": (
            'כל טענה עובדתית בתשובה נתמכת ישירות ב-tax_notes.md (מספר, שיעור, כלל, הגדרה) '
            'או התשובה מזהה נכון ששאלה היא מחוץ להיקף המסמך ("לא מצאתי את זה במסמך" / '
            'הפניה מפורשת לכך שהמסמך עוסק בשכירים בלבד). ניסוחי "צבע" גנריים שאינם טענה '
            'עובדתית (למשל "כדאי לבדוק זאת מול רואה חשבון") מותרים ואינם פוגעים בציון.'
        ),
        "ok_def": (
            "טענה עובדתית אחת מנוסחת בצורה מקורבת/לא-מדויקת ביחס למסמך (למשל עיגול מספר, "
            "ניסוח כללי מדי שמאבד תנאי), אך אין טענה שהומצאה יש מאין ואין סתירה לעובדה "
            "מפורשת במסמך."
        ),
        "bad_def": (
            "לפחות טענה עובדתית אחת שאינה במסמך כלל (מספר/כלל מומצא), או סתירה לעובדה "
            "מפורשת במסמך, או תשובה עניינית לשאלה שמחוץ להיקף המסמך במקום לזהות שאין עליה "
            'מידע (למשל "המצאת" תשובה על עצמאים/נדל"ן/מע"מ).'
        ),
        "is_programmatic": 0,
    },
    {
        "name": "Latency",
        "good_def": "≤ 2,000 ms",
        "ok_def": "2,001–5,000 ms",
        "bad_def": "> 5,000 ms",
        "is_programmatic": 1,
    },
]

GO_NO_GO = [
    {"criterion": "Grounding", "fails_unless_good": 1, "fails_if_bad": 0},
    {"criterion": "Length", "fails_unless_good": 0, "fails_if_bad": 1},
]

# Copied verbatim from assignment2/data/tax_qa_dataset.md.
TEST_QUESTIONS = [
    (1, "יש-במסמך", "מהו שיעור המס במדרגה הראשונה, ועד איזו הכנסה חודשית הוא חל?"),
    (2, "יש-במסמך", "כמה שווה נקודת זיכוי אחת בחודש ובשנה (2026)?"),
    (3, "יש-במסמך", "כמה נקודות זיכוי בסיסיות מקבל גבר, וכמה מקבלת אישה?"),
    (4, "יש-במסמך", "מהו סף המדרגה המופחתת של ביטוח לאומי ומס בריאות?"),
    (5, "יש-במסמך", "מהי תקרת ההכנסה החודשית החייבת בדמי ביטוח לאומי ומס בריאות?"),
    (6, "יש-במסמך", "מהו שיעור מס היסף, ומעל איזו הכנסה שנתית הוא חל?"),
    (7, "יש-במסמך", "מהו שיעור הפרשת העובד לפנסיית חובה במסלול המינימלי?"),
    (8, "יש-במסמך", "מהי תקרת ההפקדה הפטורה ממס לקרן השתלמות, בחודש ובשנה?"),
    (9, "יש-במסמך", "מהו שיעור זיכוי המס בגין תרומה למוסד מוכר לפי סעיף 46?"),
    (10, "יש-במסמך", "מהו הנטו המשוער לגבר עם ברוטו חודשי של 20,000 ₪, לפי טבלת הדוגמאות?"),
    (11, "יש-במסמך", "החל מאיזה סכום תרומה שנתית זכאי שכיר לזיכוי מס על תרומה?"),
    (12, "יש-במסמך", "מה השתנה במדרגות המס בעקבות רפורמת ינואר 2026?"),
    (13, "יש-במסמך", "מה ההבדל בין ניכוי מס לזיכוי מס, לפי המסמך?"),
    (14, "יש-במסמך", 'מהו "תיאום מס", ומתי שכיר צריך לבקש אותו?'),
    (15, "יש-במסמך", "עד כמה שנים אחורה ניתן להגיש דוח שנתי ולבקש החזר מס?"),
    (16, "לא-קיים-כלל", "מהו שיעור מס הרכישה על דירה שנייה בישראל?"),
    (17, "לא-קיים-כלל", "כמה מקדמות מס משלם עצמאי, ובאיזו תדירות?"),
    (18, "לא-קיים-כלל", 'מהו שיעור המע"מ הנוכחי בישראל?'),
    (19, "לא-קיים-כלל", "איך מחשבים מס שבח במכירת דירה?"),
    (20, "לא-קיים-כלל", "האם יש הטבת מס ייעודית לרכישת רכב חשמלי לשכיר?"),
    (21, "מתחכמת", "שכיר עם ברוטו חודשי של 60,000 ₪ — האם כל השכר שלו חייב בדמי ביטוח לאומי ומס בריאות?"),
    (22, "מתחכמת", "עצמאי שתרם 2,000 ₪ למוסד מוכר בשנה — כמה זיכוי מס הוא יקבל?"),
    (23, "מתחכמת", "אישה עם 2.75 נקודות זיכוי וברוטו חודשי של 13,000 ₪ — מהו מס ההכנסה הסופי שלה אחרי זיכוי, לפי הטבלה?"),
    (24, "מתחכמת", "האם הפקדה לקרן השתלמות היא חובה בחוק, כמו פנסיה?"),
]


def _table_is_empty(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
    return row["c"] == 0


def _seed_agents(conn: sqlite3.Connection) -> None:
    if not _table_is_empty(conn, "agents"):
        return
    conn.executemany(
        "INSERT INTO agents (name, description, default_model, default_system_prompt, default_temperature) "
        "VALUES (:name, :description, :default_model, :default_system_prompt, :default_temperature)",
        AGENTS,
    )


def _seed_rubric(conn: sqlite3.Connection) -> None:
    if not _table_is_empty(conn, "rubrics"):
        return
    created_at = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO rubrics (name, is_active, pass_bar_min_good, pass_bar_max_bad, created_at) "
        "VALUES (?, 1, ?, ?, ?)",
        ("assignment2_rubric_v1", 4, 0, created_at),
    )
    rubric_id = cursor.lastrowid

    for sort_order, criterion in enumerate(RUBRIC_CRITERIA):
        conn.execute(
            "INSERT INTO rubric_criteria (rubric_id, name, good_def, ok_def, bad_def, is_programmatic, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                rubric_id,
                criterion["name"],
                criterion["good_def"],
                criterion["ok_def"],
                criterion["bad_def"],
                criterion["is_programmatic"],
                sort_order,
            ),
        )

    for rule in GO_NO_GO:
        conn.execute(
            "INSERT INTO rubric_go_no_go (rubric_id, criterion, fails_unless_good, fails_if_bad) "
            "VALUES (?, ?, ?, ?)",
            (rubric_id, rule["criterion"], rule["fails_unless_good"], rule["fails_if_bad"]),
        )


def _seed_test_questions(conn: sqlite3.Connection) -> None:
    if not _table_is_empty(conn, "test_questions"):
        return
    conn.executemany(
        "INSERT INTO test_questions (id, dataset_name, category, question_text, is_active) "
        "VALUES (?, 'tax_qa_v1', ?, ?, 1)",
        [(qid, category, question_text) for qid, category, question_text in TEST_QUESTIONS],
    )


def seed_if_empty(conn: sqlite3.Connection) -> None:
    _seed_agents(conn)
    _seed_rubric(conn)
    _seed_test_questions(conn)
    conn.commit()
