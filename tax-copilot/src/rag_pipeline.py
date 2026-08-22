"""Task 4: retrieve top-K chunks, ground the answer in them, cite the sources.

answer_with_rag() is kept to the exact signature the assignment specifies and
returns nothing but the validated GroundedAnswer. Everything Task 5 needs on top
of that -- latency, tokens, which chunks came back, whether the model cited a
chunk number that was never supplied -- lives in the instrumented wrapper, so
the pipeline itself stays clean.
"""

import re
import sys
import time

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from pydantic import BaseModel

from build_index import load_index
from llm import GENERATOR_MODEL, call_structured

sys.stdout.reconfigure(encoding="utf-8")

REFUSAL_SENTENCE = "לא מצאתי את זה במסמכים המצורפים."
SEPARATOR = "\n" + "-" * 40 + "\n"

# "[2]" and "[1, 2, 8]" alike. Deliberately requires the brackets to hold
# nothing but digits, commas and spaces, so a bracketed year in the corpus text
# is not read as a citation.
CITATION_RE = re.compile(r"\[\s*\d+(?:\s*,\s*\d+)*\s*\]")


class GroundedAnswer(BaseModel):
    answer: str
    sources: list[str]
    evidence: list[str]
    answered: bool


RAG_SYSTEM_PROMPT = f"""אתה יועץ מס ידידותי ומדויק שעונה על שאלות מיסוי בישראל.

לפניך קטעים ממוספרים מתוך מסמכי מס. כללים מחייבים:
1. ענה **אך ורק** מתוך הקטעים הממוספרים שקיבלת. אל תשתמש בידע חיצוני ואל תמציא מספרים, שיעורים, סעיפי חוק או כללים.
2. צטט את מספר הקטע בסוגריים מרובעים אחרי כל טענה עובדתית — למשל: "שיעור המס הוא 25% [2]".
3. אם התשובה אינה נמצאת בקטעים, החזר ב-`answer` **בדיוק** את המשפט: "{REFUSAL_SENTENCE}" — בלי שום תוספת — וקבע `answered` ל-false.
4. אם ענית, קבע `answered` ל-true.
5. `sources`: לכל קטע שהסתמכת עליו, שם המסמך והסעיף/העמוד כפי שמופיעים בכותרת הקטע.
6. `evidence`: ציטוט מילולי מדויק של השורות שעליהן הסתמכת. אל תנסח מחדש.
7. אורך התשובה: 1–4 משפטים ממוקדים.

החזר אך ורק JSON תקני בפורמט הבא, ללא code fences וללא טקסט נוסף:
{{"answer": "...", "sources": ["..."], "evidence": ["..."], "answered": true}}"""


def _chunk_location(chunk: Document) -> str:
    md = chunk.metadata
    return f"עמוד {md['page']}" if md.get("page") else f"סעיף: {md.get('section') or 'ללא סעיף'}"


def format_context(chunks: list[Document]) -> str:
    """Numbered, separated, metadata-labelled.

    Separators are not cosmetic: five chunks concatenated bare read as one
    continuous document, and the model will happily merge a fact from chunk 1
    with a fact from chunk 4 into a sentence no source supports.
    """
    blocks = [
        f"[{i}] מסמך: {chunk.metadata['doc_name']} | {_chunk_location(chunk)}\n{chunk.page_content}"
        for i, chunk in enumerate(chunks, 1)
    ]
    return SEPARATOR.join(blocks)


def answer_with_rag(query: str, k: int = 5, vectorstore: VectorStore | None = None) -> GroundedAnswer:
    vectorstore = vectorstore or load_index()
    chunks = vectorstore.similarity_search(query, k=k)
    user_content = f"קטעים:\n{format_context(chunks)}\n\n{'=' * 40}\n\nשאלה: {query}"
    parsed, _ = call_structured(RAG_SYSTEM_PROMPT, user_content, GroundedAnswer, model=GENERATOR_MODEL)
    return parsed


def answer_with_rag_instrumented(
    query: str, k: int = 5, vectorstore: VectorStore | None = None, retriever=None,
    chunks: list[Document] | None = None,
) -> tuple[GroundedAnswer, dict]:
    """Same call plus everything Task 5/6 needs to score it.

    `retriever` overrides similarity_search for the Task 6 hybrid experiment.
    `chunks` skips retrieval entirely, for the web UI's manual-selection mode:
    the user retrieves, unticks some of what came back, and asks what the model
    answers from exactly the rest. Nothing else changes -- the same prompt, the
    same guards -- so what is measured is the context, not a second pipeline.
    """
    start = time.perf_counter()
    if chunks is None:
        vectorstore = vectorstore or load_index()
        if retriever is not None:
            chunks = retriever.invoke(query)[:k]
        else:
            chunks = vectorstore.similarity_search(query, k=k)
    user_content = f"קטעים:\n{format_context(chunks)}\n\n{'=' * 40}\n\nשאלה: {query}"
    parsed, raw = call_structured(RAG_SYSTEM_PROMPT, user_content, GroundedAnswer, model=GENERATOR_MODEL)

    # Deterministic guards -- zero LLM calls, catch what the model got wrong about itself.
    #
    # CITATION_RE matches a group, not just a lone number: the prompt asks for
    # "[2]" but the model also writes "[1, 2, 8]", and a `\[(\d+)\]` pattern
    # matches neither the group nor the numbers inside it. That is a silent
    # false negative in exactly the case worth catching -- the grouped form is
    # where an out-of-range number hides. Caught live in the web UI, where the
    # model cited [8] out of 5 supplied chunks and nothing flagged it.
    cited = {int(n) for group in CITATION_RE.findall(parsed.answer)
             for n in re.findall(r"\d+", group)}
    hallucinated_citations = sorted(n for n in cited if n < 1 or n > len(chunks))
    answered = parsed.answered
    refusal_mismatch = False
    if REFUSAL_SENTENCE in parsed.answer and answered:
        # The model set answered=True while returning the refusal sentence; trust
        # the text, not the flag.
        answered = False
        refusal_mismatch = True
    parsed = parsed.model_copy(update={"answered": answered})

    meta = {
        "latency_ms": round((time.perf_counter() - start) * 1000, 1),
        "input_tokens": raw.input_tokens,
        "output_tokens": raw.output_tokens,
        "retrieved_docs": [c.metadata["doc_name"] for c in chunks],
        "retrieved_locations": [_chunk_location(c) for c in chunks],
        "retrieved_texts": [c.page_content for c in chunks],
        "hallucinated_citations": hallucinated_citations,
        "citation_flag": bool(hallucinated_citations),
        "refusal_mismatch": refusal_mismatch,
        "k": k,
    }
    if hallucinated_citations:
        print(f"  ⚠ ציטוט מומצא: {hallucinated_citations} מתוך {len(chunks)} קטעים שסופקו")
    return parsed, meta


if __name__ == "__main__":
    # Sanity check before scaling to the full eval set: the two unanswerable
    # questions must refuse. If they do not, the grounding prompt is too weak and
    # fixing it after 34 rows have been judged is a wasted run.
    from assignment3_build_eval_set import load_eval_set
    from llm import throttle

    vectorstore = load_index()
    unanswerable = load_eval_set()[lambda d: ~d["answerable"]]
    ok = True
    for i, (_, row) in enumerate(unanswerable.iterrows()):
        throttle(i)
        result, meta = answer_with_rag_instrumented(row["question"], vectorstore=vectorstore)
        passed = not result.answered and REFUSAL_SENTENCE in result.answer
        ok &= passed
        print(f"\n{'PASS' if passed else 'FAIL'} | {row['question']}")
        print(f"  answered={result.answered} | {result.answer}")
        print(f"  אוחזרו: {meta['retrieved_docs']}")
    print(f"\n{'הסירוב עובד.' if ok else 'הסירוב נכשל — לחזק את RAG_SYSTEM_PROMPT לפני הרצה מלאה.'}")
