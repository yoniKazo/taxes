"""Hit-rate @ K -- the cheapest useful number in RAG.

No judge, no reference answer, one boolean per question, which is why Task 6
sweeps parameters against this metric before spending anything on judges.

Multi-hop rows carry semicolon-separated evidence labels; hit_at_k requires ALL
required documents to be retrieved, which is the only reading that makes a
multi-hop question meaningful. hit_at_k_any_doc is reported alongside so a
partial retrieval is visible rather than silently scored as a total miss.

Matching is at doc_name level by design: evidence_page holds the markdown
heading that precedes the chunk's START, so a chunk spanning two sections gets
labelled with the first one. Section/page agreement is recorded as a bonus
signal, never as the pass criterion.
"""


def _split_labels(value: str) -> list[str]:
    return [part.strip() for part in str(value).split(";") if part.strip()]


def hit_rate_row(evidence_doc: str, evidence_page: str, retrieved_docs: list[str],
                 retrieved_locations: list[str] | None = None) -> dict:
    required_docs = _split_labels(evidence_doc)
    if not required_docs:
        return {"hit_at_k": None, "hit_at_k_any_doc": None, "hit_page": None}

    found_docs = set(retrieved_docs)
    hits = [doc in found_docs for doc in required_docs]

    hit_page = None
    if retrieved_locations:
        required_pages = _split_labels(evidence_page)
        locations = " | ".join(retrieved_locations)
        hit_page = all(page in locations for page in required_pages) if required_pages else None

    return {"hit_at_k": all(hits), "hit_at_k_any_doc": any(hits), "hit_page": hit_page}
