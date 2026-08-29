"""מטלה 4, Task 2 -- שלושת ה-tools של ה-agent.

`search_tax_corpus` עוטף את הרטריבר של מטלה 3. `calculator` ו-`calculate_tax_refund`
הם שני ה-tools שעושים חשבון שאין בשום קורפוס -- `calculator` באופן גנרי,
`calculate_tax_refund` על ההיקף המדויק ש-tax_refund_calculator.py כבר מכסה
(מס הכנסה לשכיר).

חוזה הכישלון של כל tool: להחזיר מחרוזת מסבירה "ERROR: ..." / "NO_RESULTS: ...".
לעולם לא raise, לעולם לא להחזיר None או "".

התנגשות שם, מתועדת ולא נפתרת: `mcp_servers/tax_corpus.py` מגדיר tool נפרד בשם
זהה `search_tax_corpus`, חשוף ל-Claude Code עצמו בזמן פיתוח -- לא קשור ל-agent
של האפליקציה הזו. namespaces נפרדים לגמרי, תהליכים נפרדים, אין התנגשות
פונקציונלית; רק לשים לב בחיפוש טקסטואלי בקוד.
"""

import ast
import operator
import sys

from langchain_core.tools import tool

from build_index import load_index
from rag_pipeline import format_context
from tax_refund_calculator import InvalidInputError, calculate

sys.stdout.reconfigure(encoding="utf-8")

# --- calculator ---------------------------------------------------------------

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_ALLOWED_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _eval_node(node: ast.AST) -> float:
    """Whitelist-only: numbers, +-*/**%, parentheses, unary +/-. No names, no
    calls, no attributes -- the input is LLM-generated, so a bare eval() would
    be arbitrary code execution, not a calculator."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        return _ALLOWED_UNARYOPS[type(node.op)](_eval_node(node.operand))
    raise ValueError(f"תו/מבנה לא נתמך: {ast.dump(node)}")


@tool
def calculator(expression: str) -> str:
    """מחשבון אריתמטי כללי. מקבל ביטוי מתמטי בודד (מספרים, + - * / ** % וסוגריים
    בלבד -- למשל "0.18 * 4390" או "(1978745 * 0.08)") ומחזיר את התוצאה כמחרוזת,
    מעוגלת ל-2 ספרות אחרי הנקודה.
    לא תומך במשתנים, בפונקציות, או בכל דבר מעבר לאריתמטיקה בסיסית.
    בכשל (חילוק באפס, ביטוי פגום, תו לא נתמך) מחזיר "ERROR: <הסבר>" -- לעולם לא raise.
    """
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
    except ZeroDivisionError:
        return f"ERROR: חילוק באפס בביטוי '{expression}'."
    except Exception as e:  # noqa: BLE001 -- כל כשל פרסינג/הערכה הופך לתשובת ERROR, לא לחריגה
        return f"ERROR: לא ניתן לחשב את '{expression}': {e}"
    if isinstance(result, float) and result.is_integer():
        return str(int(result))
    return str(round(result, 2))


# --- calculate_tax_refund ------------------------------------------------------


@tool
def calculate_tax_refund(
    gross_salary: float,
    gender: str,
    extra_credit_points: float = 0.0,
    pension_employee_pct: float = 0.0,
    keren_hishtalmut_monthly: float = 0.0,
    annual_donation: float = 0.0,
) -> str:
    """**זהו ה-tool הנכון לכל שאלה על גובה זיכוי מס/חיסכון מס/נטו של שכיר מסוים -- כולל
    זיכוי מתרומה (סעיף 46), פנסיה, או קרן השתלמות -- ברגע שיש שכר חודשי נתון.** אם
    search_tax_corpus לא מצא תשובה ישירה לשאלת זיכוי כזו, זה **לא** אומר שאי אפשר לחשב --
    זה בדיוק המקרה שבו tool זה נדרש: הוא מחשב את הזיכוי ישירות מהנתונים, בלי תלות במה
    שהקורפוס מחזיר. אל תסיק "אי אפשר לחשב" על שאלת זיכוי/נטו לשכיר לפני שניסית אותו.

    מחשב מס הכנסה, ביטוח לאומי/בריאות ונטו חודשי לשכיר בישראל, שנת מס 2026 בלבד.
    קלט: gross_salary (שכר ברוטו חודשי, ש"ח, חייב להיות חיובי), gender ("male"/"female"),
    extra_credit_points (נקודות זיכוי נוספות מעבר לבסיס), pension_employee_pct (אחוז
    הפרשת עובד לפנסיה, 0-1), keren_hishtalmut_monthly (הפקדה חודשית לקרן השתלמות, ש"ח),
    annual_donation (סכום תרומה שנתי לצורך זיכוי סעיף 46, ש"ח).
    מחזיר טקסט עם: מס הכנסה לפני/אחרי זיכוי, ביטוח לאומי, מס בריאות, נטו משוער,
    וחיסכון המס מפנסיה/קרן השתלמות/תרומה אם רלוונטי.
    מכסה **שכירים בלבד** -- לא עצמאים, לא מס רווחי הון, לא מס שבח/רכישה, לא מע"מ
    (לאלה יש להשתמש ב-search_tax_corpus ואז ב-calculator).
    בקלט לא תקין (שכר לא חיובי, gender לא "male"/"female") מחזיר "ERROR: <הסבר>" -- לעולם לא raise.
    """
    try:
        result = calculate(
            gross_salary=gross_salary,
            gender=gender,
            extra_credit_points=extra_credit_points,
            pension_employee_pct=pension_employee_pct,
            keren_hishtalmut_monthly=keren_hishtalmut_monthly,
            annual_donation=annual_donation,
        )
    except InvalidInputError as e:
        return f"ERROR: {e}"

    lines = [
        f"מס הכנסה לפני זיכוי: {result.tax_before_credit:.2f} ₪",
        f"מס הכנסה אחרי זיכוי: {result.tax_after_credit:.2f} ₪",
        f"ביטוח לאומי: {result.national_insurance:.2f} ₪",
        f"מס בריאות: {result.health_tax:.2f} ₪",
        f"נטו משוער: {result.net:.2f} ₪",
    ]
    if pension_employee_pct > 0:
        lines.append(f"חיסכון מס מהפרשת פנסיה: {result.pension_tax_savings:.2f} ₪")
    if keren_hishtalmut_monthly > 0:
        lines.append(f"חיסכון מס מקרן השתלמות: {result.keren_hishtalmut_tax_savings:.2f} ₪")
    if annual_donation > 0:
        lines.append(f"זיכוי מס שנתי מתרומה (סעיף 46): {result.donation_credit_annual:.2f} ₪")
    return "\n".join(lines)


# --- search_tax_corpus ----------------------------------------------------------

_vectorstore_cache = None


def _get_vectorstore():
    global _vectorstore_cache
    if _vectorstore_cache is None:
        _vectorstore_cache = load_index()
    return _vectorstore_cache


def _search_tax_corpus_impl(query: str, k: int, vectorstore) -> str:
    """מופרד מה-tool עצמו כדי שבדיקות יחידה יוכלו להזריק vectorstore מזויף,
    בלי לטעון FAISS/embeddings אמיתיים בכל הרצת pytest."""
    chunks = vectorstore.similarity_search(query, k=k)
    if not chunks:
        return f"NO_RESULTS: לא נמצא אף קטע התואם ל-'{query}'. נסה שאילתה רחבה יותר או מונח אחר."
    return format_context(chunks)


@tool
def search_tax_corpus(query: str, k: int = 5) -> str:
    """מחפש בקורפוס המיסוי הישראלי (6 מסמכים: שכירים, עצמאים, שוק ההון, מקרקעין,
    כללי, ולוח עזר רשמי של רשות המסים -- ראו assignment3/data/corpus_manifest.json).
    מחזיר עד k קטעים רלוונטיים (ברירת מחדל 5), כל אחד עם שם המסמך והסעיף/עמוד שלו.
    מחזיר "NO_RESULTS: <query>" אם שום קטע לא נמצא דומה מספיק.
    לא מכסה: חדשות/עדכוני חוק אחרי מועד איסוף הקורפוס, שאלות שאינן מיסוי, וחישוב --
    לחישוב יש להשתמש ב-calculator או ב-calculate_tax_refund על הנתונים שהוחזרו כאן.
    """
    return _search_tax_corpus_impl(query, k, _get_vectorstore())
