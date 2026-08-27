"""מטלה 4, Task 1: מערך 24 המשימות + הקפאת ה-baseline.

הרכב: 6 multi_hop (5 מהן search_tax_corpus+calculator, 1 גם +calculate_tax_refund),
3 no_tool, 3 unanswerable, 2 tool_fails, 10 single.

מספרי הייחוס ל-calculate_tax_refund חושבו ישירות מ-tax_refund_calculator.calculate()
(לא בחישוב ידני), כדי שהם יהיו תואמים-בהכרח למכשיר שגם ה-agent קורא לו.
מספרי הייחוס לשאלות retrieval/calculator מבוססים על TaxData/ בפועל (ראו source_note
בכל שורה) -- לא הומצאו.

expected_tools הוא מלכודת מכוונת (לשון המטלה): מתועד ב-trace לצורך דיבאג בלבד,
אף פעם לא לניקוד -- ראו plans/assignment4-plan.md.
"""

import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from tax_refund_calculator import calculate  # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(SCRIPT_DIR, "..", "assignment4", "data", "tasks.csv")

# Assignment 3's frozen baseline commit (RAG index/k/prompt/model pinned there) --
# recorded here, not just in the writeup, so the eval runner can assert against it.
FROZEN_BASELINE_COMMIT = "39692df"

_s1 = calculate(15000.0, "male")
_s6 = calculate(18000.0, "female", annual_donation=5000.0)
_s9 = calculate(30000.0, "male", pension_employee_pct=0.06)
_mh6_employee = calculate(20000.0, "male")

TASKS = [
    # --- multi_hop (6) ---------------------------------------------------------
    {
        "task_id": "mh1",
        "task": "כמה מס רכישה אשלם על דירה שנייה (לא דירה יחידה) בשווי 4,000,000 ₪?",
        "success_criteria": 'answer contains "320,000" or "320000" (±1)',
        "reference_answer": "מס רכישה על דירה נוספת הוא 8% מהשקל הראשון עד 6,055,070 ₪ (הוראת שעה, סעיף 9(ג1ו)). "
        "8% * 4,000,000 = 320,000 ₪.",
        "type": "multi_hop",
        "expected_tools": "search_tax_corpus,calculator",
        "answerable": True,
    },
    {
        "task_id": "mh2",
        "task": 'מהו שיעור המע"מ הנוכחי בישראל, וכמה אשלם בסה"כ (כולל מע"מ) על שירות שעלותו 4,390 ₪ לפני מע"מ?',
        "success_criteria": 'answer contains "5,180.2" or "5180.2" (±0.01)',
        "reference_answer": 'שיעור המע"מ הוא 18%. 4,390 * 1.18 = 5,180.20 ₪ (מתוכם 790.20 ₪ מע"מ).',
        "type": "multi_hop",
        "expected_tools": "search_tax_corpus,calculator",
        "answerable": True,
    },
    {
        "task_id": "mh3",
        "task": "מהו מס רווח ההון על רווח הון ריאלי של 200,000 ₪ ממכירת מניות, עבור מי שאינו בעל מניות מהותי?",
        "success_criteria": 'answer contains "50,000" or "50000" (±1)',
        "reference_answer": "שיעור מס רווח הון הכללי הוא 25% (סעיף 91 לפקודה). 25% * 200,000 = 50,000 ₪.",
        "type": "multi_hop",
        "expected_tools": "search_tax_corpus,calculator",
        "answerable": True,
    },
    {
        "task_id": "mh4",
        "task": "כמה מס רכישה אשלם על משרד (נכס שאינו למגורים) בשווי 1,500,000 ₪?",
        "success_criteria": 'answer contains "90,000" or "90000" (±1)',
        "reference_answer": "מס רכישה על נכס שאינו למגורים הוא 6% אחיד ללא מדרגות (תקנה 2(1) לתקנות מס רכישה). "
        "6% * 1,500,000 = 90,000 ₪.",
        "type": "multi_hop",
        "expected_tools": "search_tax_corpus,calculator",
        "answerable": True,
    },
    {
        "task_id": "mh5",
        "task": "פרויקט תכנוני העלה את שווי המקרקעין שלי ב-300,000 ₪. כמה היטל השבחה אצטרך לשלם?",
        "success_criteria": 'answer contains "150,000" or "150000" (±1)',
        "reference_answer": "שיעור היטל ההשבחה הוא 50% מסכום ההשבחה. 50% * 300,000 = 150,000 ₪.",
        "type": "multi_hop",
        "expected_tools": "search_tax_corpus,calculator",
        "answerable": True,
    },
    {
        "task_id": "mh6",
        "task": "לשכיר עם משכורת 20,000 ₪ לחודש (גבר, ללא נקודות זיכוי נוספות) ולעצמאי עם אותה הכנסה חודשית — "
        "למי דמי הביטוח הלאומי ומס הבריאות גבוהים יותר בחודש, ובכמה?",
        "success_criteria": 'answer contains "981" (±2) and indicates the self-employed pays more',
        "reference_answer": (
            f"שכיר: ביטוח לאומי {_mh6_employee.national_insurance:.2f} + מס בריאות {_mh6_employee.health_tax:.2f} "
            f"= {_mh6_employee.national_insurance + _mh6_employee.health_tax:.2f} ₪. עצמאי: 7.7% על 7,703 הראשונים "
            "(593.13 ₪) ו-18% על ה-12,297 הנותרים (2,213.46 ₪) = 2,806.59 ₪. "
            "העצמאי משלם 981.13 ₪ יותר בחודש."
        ),
        "type": "multi_hop",
        "expected_tools": "search_tax_corpus,calculator,calculate_tax_refund",
        "answerable": True,
    },
    # --- no_tool (3): success means zero tool calls -----------------------------
    {
        "task_id": "nt1",
        "task": "מה אתה יכול לעזור לי איתו?",
        "success_criteria": "tool_calls == 0",
        "reference_answer": "תיאור כללי של יכולות המערכת (שאלות מס, חישובי מס, לא צריך לקרוא לשום tool).",
        "type": "no_tool",
        "expected_tools": "",
        "answerable": True,
    },
    {
        "task_id": "nt2",
        "task": "במילים כלליות, בלי לחפש שום דבר: מה זה בכלל 'נקודת זיכוי' במס הכנסה?",
        "success_criteria": "tool_calls == 0",
        "reference_answer": "הסבר כללי ממקור-הידע הפנימי של המודל, ללא קריאה לקורפוס או למחשבון.",
        "type": "no_tool",
        "expected_tools": "",
        "answerable": True,
    },
    {
        "task_id": "nt3",
        "task": "שלום! מה שלומך היום?",
        "success_criteria": "tool_calls == 0",
        "reference_answer": "ברכה כללית, ללא תוכן מס, לא צריכה שום tool.",
        "type": "no_tool",
        "expected_tools": "",
        "answerable": True,
    },
    # --- unanswerable (3): bounded refusal, not a 12-step hunt ------------------
    {
        "task_id": "ua1",
        "task": "מהו שיעור מס החברות בישראל בשנת 2026?",
        "success_criteria": "refused == True",
        "reference_answer": 'לא מצאתי את זה בקורפוס. הקורפוס עוסק במיסוי יחידים; "מס חברות" מוזכר רק בהקשר סיווג '
        "הכנסה מכרייה קריפטוגרפית, בלי שהשיעור עצמו ניתן במפורש.",
        "type": "unanswerable",
        "expected_tools": "search_tax_corpus",
        "answerable": False,
    },
    {
        "task_id": "ua2",
        "task": "כיצד מחושבת הארנונה על דירת מגורים, ומהם התעריפים?",
        "success_criteria": "refused == True",
        "reference_answer": "לא מצאתי את זה בקורפוס. ארנונה היא מס עירוני שאינו מופיע בשום מקום בקורפוס, גם לא במדריך המקרקעין.",
        "type": "unanswerable",
        "expected_tools": "search_tax_corpus",
        "answerable": False,
    },
    {
        "task_id": "ua3",
        "task": "מה מזג האוויר הצפוי מחר בתל אביב?",
        "success_criteria": "refused == True and tool_calls <= 2",
        "reference_answer": "שאלה שאינה קשורה למיסוי כלל ואינה נגזרת משום tool זמין. סירוב מהיר, בלי חיפוש ממושך.",
        "type": "unanswerable",
        "expected_tools": "",
        "answerable": False,
    },
    # --- tool_fails (2): the flagged tool returns its error string on purpose ---
    {
        "task_id": "tf1",
        "task": "מהי מדרגת המס הראשונה על הכנסת שכיר, ובאיזה שיעור?",
        "success_criteria": "refused == True (reports search_tax_corpus failure, does not fabricate a rate)",
        "reference_answer": "עם search_tax_corpus שבור: המערכת אמורה לדווח שאינה יכולה להשלים את המשימה -- לא להמציא מדרגה.",
        "type": "tool_fails",
        "expected_tools": "search_tax_corpus",
        "answerable": True,
        "break_tool": "search_tax_corpus",
    },
    {
        "task_id": "tf2",
        "task": "כמה זה 15% מ-50,000 ₪?",
        "success_criteria": "refused == True (reports calculator failure, does not fabricate a number)",
        "reference_answer": "עם calculator שבור: המערכת אמורה לדווח שאינה יכולה להשלים את המשימה -- לא להמציא תוצאה (7,500 ₪).",
        "type": "tool_fails",
        "expected_tools": "calculator",
        "answerable": True,
        "break_tool": "calculator",
    },
    # --- single (10): one tool call, the control group --------------------------
    {
        "task_id": "s1",
        "task": "כמה נטו יקבל שכיר עם משכורת 15,000 ₪ (גבר, ללא נקודות זיכוי נוספות)?",
        "success_criteria": f'answer contains "{_s1.net:.2f}" (±0.5)',
        "reference_answer": f"נטו {_s1.net:.2f} ₪ (מס אחרי זיכוי {_s1.tax_after_credit:.2f}, ביטוח לאומי "
        f"{_s1.national_insurance:.2f}, מס בריאות {_s1.health_tax:.2f}).",
        "type": "single",
        "expected_tools": "calculate_tax_refund",
        "answerable": True,
    },
    {
        "task_id": "s2",
        "task": "מהי תקרת הפטור ממס שבח לדירת מגורים יחידה?",
        "success_criteria": 'answer contains "5,008,000" or "5008000" (±1)',
        "reference_answer": "5,008,000 ₪ לתקופה 1.1.2025–31.12.2027 (סעיף 49א(א1) לחוק, הוראת ביצוע 1/2026).",
        "type": "single",
        "expected_tools": "search_tax_corpus",
        "answerable": True,
    },
    {
        "task_id": "s3",
        "task": "מהי תקרת ההכנסה החייבת בדמי ביטוח לאומי לחודש, לשנת 2026?",
        "success_criteria": 'answer contains "51,910" or "51910" (±1)',
        "reference_answer": "51,910 ₪ לחודש -- תקרה מוחלטת, לא מדרגה נוספת.",
        "type": "single",
        "expected_tools": "search_tax_corpus",
        "answerable": True,
    },
    {
        "task_id": "s4",
        "task": "כמה זה 12,297 כפול 0.07?",
        "success_criteria": 'answer contains "860.79"',
        "reference_answer": "860.79",
        "type": "single",
        "expected_tools": "calculator",
        "answerable": True,
    },
    {
        "task_id": "s5",
        "task": 'מהו שיעור המע"מ הנוכחי בישראל?',
        "success_criteria": 'answer contains "18%"',
        "reference_answer": '18% (עלה מ-17% ב-1.1.2025, ונשאר כך גם ב-2026).',
        "type": "single",
        "expected_tools": "search_tax_corpus",
        "answerable": True,
    },
    {
        "task_id": "s6",
        "task": "שכירה עם משכורת 18,000 ₪ (אישה) תורמת 5,000 ₪ בשנה. מה גובה זיכוי המס השנתי שלה מהתרומה?",
        "success_criteria": f'answer contains "{_s6.donation_credit_annual:.2f}" or "{_s6.donation_credit_annual:.0f}" (±1)',
        "reference_answer": f"זיכוי מס שנתי {_s6.donation_credit_annual:.2f} ₪ (35% מהתרומה, שעברה את הסף המינימלי).",
        "type": "single",
        "expected_tools": "calculate_tax_refund",
        "answerable": True,
    },
    {
        "task_id": "s7",
        "task": "מהו שיעור מס הרכישה על רכישת קרקע חקלאית, על חלק השווי עד 631,335 ₪?",
        "success_criteria": 'answer contains "0.5%"',
        "reference_answer": "0.5% (תקנה 16 לתקנות מס רכישה, בתוקף 16.1.2026–15.1.2027).",
        "type": "single",
        "expected_tools": "search_tax_corpus",
        "answerable": True,
    },
    {
        "task_id": "s8",
        "task": "מהו שיעור המס על ריבית מתאגיד בנקאי על נכס שאינו צמוד למדד?",
        "success_criteria": 'answer contains "15%"',
        "reference_answer": "15% (תקנה 4 לתקנות ניכוי מריבית/דיבידנד).",
        "type": "single",
        "expected_tools": "search_tax_corpus",
        "answerable": True,
    },
    {
        "task_id": "s9",
        "task": "שכיר עם משכורת 30,000 ₪ (גבר) מפריש 6% מהמשכורת לפנסיה. מה חיסכון המס החודשי שלו מזה?",
        "success_criteria": f'answer contains "{_s9.pension_tax_savings:.2f}" or "{_s9.pension_tax_savings:.0f}" (±1)',
        "reference_answer": f"חיסכון מס חודשי מהפרשת הפנסיה: {_s9.pension_tax_savings:.2f} ₪.",
        "type": "single",
        "expected_tools": "calculate_tax_refund",
        "answerable": True,
    },
    {
        "task_id": "s10",
        "task": "כמה זה 2,347,040 פחות 1,978,745?",
        "success_criteria": 'answer contains "368,295" or "368295"',
        "reference_answer": "368,295",
        "type": "single",
        "expected_tools": "calculator",
        "answerable": True,
    },
]


def build_tasks_df() -> pd.DataFrame:
    return pd.DataFrame(TASKS)


if __name__ == "__main__":
    df = build_tasks_df()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    counts = df["type"].value_counts().to_dict()
    print(f"{len(df)} משימות נכתבו ל-{os.path.abspath(OUT_PATH)}")
    print(f"הרכב: {counts}")
    print(f"baseline קפוא: commit {FROZEN_BASELINE_COMMIT}")
