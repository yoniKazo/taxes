"""Task 4 runner: answer every eval question with RAG and persist everything.

Writes JSON rather than CSV because the retrieved chunk texts must survive intact
for the Task 5 judges -- faithfulness and context relevance are judged against
the exact chunks the model saw, not a re-retrieval that might differ.
"""

import json
import os
import sys

from assignment3_build_eval_set import load_eval_set
from build_index import load_index
from llm import throttle
from rag_pipeline import answer_with_rag_instrumented

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "assignment3", "data", "rag_results.json")

DEFAULT_K = 5


def run(k: int = DEFAULT_K, vectorstore=None, retriever=None, output_path: str = OUTPUT_PATH) -> list[dict]:
    eval_set = load_eval_set()
    vectorstore = vectorstore or load_index()

    rows = []
    for i, (_, row) in enumerate(eval_set.iterrows()):
        print(f"[{i + 1}/{len(eval_set)}] id={row['id']} ({row['category']}) {row['question'][:55]}")
        throttle(i)
        answer, meta = answer_with_rag_instrumented(
            row["question"], k=k, vectorstore=vectorstore, retriever=retriever
        )
        rows.append({
            "id": int(row["id"]),
            "rag_answer": answer.answer,
            "rag_sources": answer.sources,
            "rag_evidence": answer.evidence,
            "rag_answered": answer.answered,
            **meta,
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"\n{len(rows)} שורות -> {output_path}")
    flagged = sum(r["citation_flag"] for r in rows)
    mismatched = sum(r["refusal_mismatch"] for r in rows)
    print(f"ציטוטים מומצאים שנתפסו בקוד: {flagged}/{len(rows)}")
    print(f"אי-התאמה בין answered לטקסט הסירוב: {mismatched}/{len(rows)}")
    return rows


def load_rag_results(path: str = OUTPUT_PATH) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    run()
