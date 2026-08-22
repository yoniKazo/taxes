"""Task 2 (synthetic half): generate questions from sampled chunks.

Hands one chunk to the generator model and asks for a question that chunk
answers. The chunk's own doc_name/section/page becomes the retrieval ground
truth for free -- which is the whole reason to generate questions this way.

These are all labelled difficulty=easy on purpose: a question written FROM one
chunk is answerable BY one chunk, so top-K retrieval flatters itself. The six
genuinely hard questions are hand-written in hard_questions.py.
"""

import csv
import os
import random
import re
import sys

from pydantic import BaseModel

from build_index import build_chunks
from llm import call_structured, throttle

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "assignment3", "data", "synthetic_questions.csv")

CHUNKS_PER_DOC = 5
MIN_CHUNK_CHARS = 400
SEED = 20260818
# Every md guide ends with a link table; those chunks carry no answerable fact and
# the generator rejects them anyway, so filtering here just stops wasting calls.
MAX_URL_SHARE = 0.15

SYSTEM_PROMPT = """אתה בונה מערך הערכה (eval set) לבוט שאלות-תשובות על מיסוי בישראל.

מקבל: קטע אחד מתוך מדריך מס.
מחזיר: שאלה אחת שמשתמש אמיתי היה שואל, שהקטע הזה עונה עליה במלואו, והתשובה המדויקת לפי הקטע.

כללים:
1. השאלה חייבת להיות ניתנת למענה מהקטע הזה בלבד — בלי ידע חיצוני.
2. השאלה צריכה להישמע כמו שאלה של אדם אמיתי, לא כמו שאלת מבחן. אל תתחיל ב"לפי הקטע" או "לפי המסמך".
3. התשובה חייבת לצטט את המספר/השיעור/הכלל המדויק מהקטע. בלי לעגל ובלי להוסיף.
4. אם הקטע הוא רשימת מקורות/קישורים בלבד וללא תוכן מהותי — החזר question ריק.
5. עברית בלבד.

החזר אך ורק JSON: {"question": "...", "reference_answer": "..."}"""


class GeneratedQuestion(BaseModel):
    question: str
    reference_answer: str


def is_link_dump(chunk) -> bool:
    text = chunk.page_content
    url_chars = sum(len(m) for m in re.findall(r"https?://\S+", text))
    section = (chunk.metadata.get("section") or "")
    return url_chars / max(len(text), 1) > MAX_URL_SHARE or section.startswith("מקורות")


def sample_chunks() -> list:
    chunks, _ = build_chunks()
    rng = random.Random(SEED)
    by_doc: dict[str, list] = {}
    for chunk in chunks:
        if len(chunk.page_content) >= MIN_CHUNK_CHARS and not is_link_dump(chunk):
            by_doc.setdefault(chunk.metadata["doc_name"], []).append(chunk)

    sampled = []
    for doc_name in sorted(by_doc):
        pool = by_doc[doc_name]
        sampled.extend(rng.sample(pool, min(CHUNKS_PER_DOC, len(pool))))
    return sampled


def evidence_page(chunk) -> str:
    md = chunk.metadata
    return str(md["page"]) if md.get("page") else (md.get("section") or "")


def main() -> None:
    sampled = sample_chunks()
    print(f"{len(sampled)} צ'אנקים נדגמו ({CHUNKS_PER_DOC} לכל מסמך, מינימום {MIN_CHUNK_CHARS} תווים)")

    rows = []
    for i, chunk in enumerate(sampled):
        md = chunk.metadata
        print(f"[{i + 1}/{len(sampled)}] {md['doc_name']} | {evidence_page(chunk)[:50]}")
        throttle(i)
        generated, _ = call_structured(SYSTEM_PROMPT, chunk.page_content, GeneratedQuestion)
        if not generated.question.strip():
            print("     (דילוג: הקטע סומן כחסר תוכן מהותי)")
            continue
        rows.append({
            "question": generated.question.strip(),
            "reference_answer": generated.reference_answer.strip(),
            "evidence_doc": md["doc_name"],
            "evidence_page": evidence_page(chunk),
            "answerable": True,
            "difficulty": "easy",
            "category": "synthetic",
        })

    with open(OUTPUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n{len(rows)} שאלות נכתבו ל-{OUTPUT_PATH}")


if __name__ == "__main__":
    main()
