"""Indexing, retrieval and hit-rate. Still zero LLM calls.

Everything the assignment calls "free" lives here: chunking, embedding (local),
similarity search, chunk browsing, and hit-rate@K. The expensive half is in
generation.py and this module never imports it.

Three things the CLI scripts get away with and a UI cannot -- see the inline
notes on _to_similarity(), hybrid_retriever() and build_index_with_progress().
"""

import hashlib
import json
import os
import random
import shutil
from typing import Callable

from langchain_core.documents import Document

from api.rag import SRC_DIR  # noqa: F401  -- puts src/ on sys.path

import build_index
from embeddings import BGE_MODEL, E5_MODEL, PrefixedEmbeddings
from retrieval_eval import hit_rate_row

ASSIGNMENT_DIR = os.path.abspath(os.path.join(SRC_DIR, "..", "assignment3"))
DEFAULT_INDEX_DIR = os.path.join(ASSIGNMENT_DIR, "index")
CUSTOM_INDEX_ROOT = os.path.join(ASSIGNMENT_DIR, "index_custom")

DEFAULT_INDEX_ID = "default"
EMBEDDING_MODELS = [E5_MODEL, BGE_MODEL]
EMBED_BATCH_SIZE = 32

# The default index is the graded artifact: every assignment3_*.py script loads
# it, and the write-up's numbers were measured against it. The UI reads it and
# never writes to it -- rebuilds always land under index_custom/.
READ_ONLY_INDEX_IDS = {DEFAULT_INDEX_ID}


class IndexNotFound(Exception):
    pass


class ReadOnlyIndex(Exception):
    pass


# --- index identity ---------------------------------------------------------


def config_slug(doc_names: list[str], chunk_size: int, chunk_overlap: int, model: str) -> str:
    """Deterministic id, so rebuilding the same config reuses the same folder
    instead of littering the disk with identical indexes."""
    payload = json.dumps(
        {"docs": sorted(doc_names), "size": chunk_size, "overlap": chunk_overlap, "model": model},
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()[:10]
    return f"c{chunk_size}-o{chunk_overlap}-{model.split('/')[-1]}-{digest}"


def index_dir(index_id: str) -> str:
    if index_id == DEFAULT_INDEX_ID:
        return DEFAULT_INDEX_DIR
    path = os.path.join(CUSTOM_INDEX_ROOT, index_id)
    if not os.path.isdir(path):
        raise IndexNotFound(f"אינדקס לא נמצא: {index_id}")
    return path


def index_meta(index_id: str) -> dict:
    if index_id == DEFAULT_INDEX_ID:
        manifest = build_index.load_manifest()
        return {
            "index_id": DEFAULT_INDEX_ID,
            "label": "האינדקס הקנוני של מטלה 3",
            "doc_names": [entry["doc_name"] for entry in manifest],
            "chunk_size": build_index.CHUNK_SIZE,
            "chunk_overlap": build_index.CHUNK_OVERLAP,
            "embedding_model": E5_MODEL,
            "chunk_count": sum(baseline_chunk_counts().values()),
            "read_only": True,
        }
    path = os.path.join(index_dir(index_id), "meta.json")
    with open(path, "r", encoding="utf-8") as f:
        return {**json.load(f), "read_only": False}


def list_indexes() -> list[dict]:
    out = [index_meta(DEFAULT_INDEX_ID)]
    if os.path.isdir(CUSTOM_INDEX_ROOT):
        for name in sorted(os.listdir(CUSTOM_INDEX_ROOT)):
            if os.path.exists(os.path.join(CUSTOM_INDEX_ROOT, name, "meta.json")):
                out.append(index_meta(name))
    return out


def delete_index(index_id: str) -> None:
    if index_id in READ_ONLY_INDEX_IDS:
        raise ReadOnlyIndex("האינדקס הקנוני של מטלה 3 מוגן — אי אפשר למחוק אותו מה-UI.")
    shutil.rmtree(index_dir(index_id))
    _vectorstore_cache.pop(index_id, None)
    _chunk_cache.pop(index_id, None)


# --- chunking (no embedding, instant) ---------------------------------------

_chunk_cache: dict[str, list[Document]] = {}


def chunks_for_config(
    doc_names: list[str] | None = None,
    chunk_size: int = build_index.CHUNK_SIZE,
    chunk_overlap: int = build_index.CHUNK_OVERLAP,
) -> list[Document]:
    """Parse + split + enrich. No embedding, so this is fast enough to run on
    every keystroke of the chunk-size field -- which is the point: the user sees
    the chunk count before paying the CPU minutes an actual rebuild costs."""
    manifest = build_index.load_manifest()
    # None means "the whole corpus"; an empty list means the user unticked every
    # document, which is an error rather than a silent fallback to all of them.
    if doc_names is not None:
        wanted = set(doc_names)
        manifest = [entry for entry in manifest if entry["doc_name"] in wanted]
    if not manifest:
        raise ValueError("לא נבחר אף מסמך.")
    chunks = build_index.split_documents(
        build_index.load_raw_documents(manifest), chunk_size, chunk_overlap
    )
    build_index.enrich_section_metadata(chunks, manifest)
    return chunks


def baseline_chunk_counts() -> dict[str, int]:
    """Per-document chunk count at the assignment's fixed 1000/150 baseline."""
    key = "__baseline__"
    if key not in _chunk_cache:
        _chunk_cache[key] = chunks_for_config()
    counts: dict[str, int] = {}
    for chunk in _chunk_cache[key]:
        name = chunk.metadata["doc_name"]
        counts[name] = counts.get(name, 0) + 1
    return counts


def preview_chunks(
    doc_names: list[str] | None,
    chunk_size: int,
    chunk_overlap: int,
    sample: int = 3,
) -> dict:
    chunks = chunks_for_config(doc_names, chunk_size, chunk_overlap)
    per_doc: dict[str, int] = {}
    lengths = []
    for chunk in chunks:
        name = chunk.metadata["doc_name"]
        per_doc[name] = per_doc.get(name, 0) + 1
        lengths.append(len(chunk.page_content))
    return {
        "chunk_count": len(chunks),
        "per_doc": per_doc,
        "mean_chars": round(sum(lengths) / len(lengths), 1) if lengths else 0,
        "min_chars": min(lengths, default=0),
        "max_chars": max(lengths, default=0),
        "sample": [_chunk_payload(c) for c in chunks[:sample]],
    }


# --- chunk browsing (Task 3: "actually look at it") -------------------------


def _chunk_payload(chunk: Document, rank: int | None = None, score: float | None = None) -> dict:
    md = chunk.metadata
    return {
        "rank": rank,
        "score": score,
        "doc_name": md.get("doc_name"),
        "doc_format": md.get("doc_format"),
        "topic": md.get("topic"),
        "source_url": md.get("source_url"),
        "page": md.get("page"),
        "section": md.get("section"),
        "chunk_index": md.get("chunk_index"),
        "location": (f"עמוד {md['page']}" if md.get("page")
                     else f"סעיף: {md.get('section') or 'ללא סעיף'}"),
        "text": chunk.page_content,
        "chars": len(chunk.page_content),
    }


def browse_chunks(
    index_id: str = DEFAULT_INDEX_ID,
    doc_name: str | None = None,
    doc_format: str | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 10,
    seed: int | None = None,
) -> dict:
    """Read the corpus the way Task 3 demands, instead of taking the write-up's
    word for what the parser did. `seed` switches to random sampling, which is
    the exact 10-random-chunks step build_index.py prints on the CLI."""
    meta = index_meta(index_id)
    chunks = chunks_for_config(
        meta["doc_names"], meta["chunk_size"], meta["chunk_overlap"]
    )
    if doc_name:
        chunks = [c for c in chunks if c.metadata["doc_name"] == doc_name]
    if doc_format:
        chunks = [c for c in chunks if c.metadata.get("doc_format") == doc_format]
    if search:
        chunks = [c for c in chunks if search in c.page_content]
    total = len(chunks)
    if seed is not None:
        selected = random.Random(seed).sample(chunks, min(limit, total))
    else:
        selected = chunks[offset:offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "seed": seed,
        "chunks": [_chunk_payload(c) for c in selected],
    }


# --- retrieval --------------------------------------------------------------

_vectorstore_cache: dict[str, object] = {}


def get_vectorstore(index_id: str = DEFAULT_INDEX_ID):
    """Loading a FAISS index also loads sentence-transformers and torch, which
    is seconds on a cold start -- cached for the process lifetime."""
    if index_id not in _vectorstore_cache:
        meta = index_meta(index_id)
        embeddings = PrefixedEmbeddings(meta["embedding_model"])
        _vectorstore_cache[index_id] = build_index.load_index(
            embeddings, index_dir=index_dir(index_id)
        )
    return _vectorstore_cache[index_id]


def _to_similarity(l2_distance: float) -> float:
    """FAISS IndexFlatL2 returns a DISTANCE -- lower is better.

    Rendering it directly as a "similarity" meter would draw the best chunk as
    the emptiest bar. Both embedding models are encoded with
    normalize_embeddings=True (see src/embeddings.py), so the vectors are unit
    length and L2^2 = 2 - 2*cos gives the conversion exactly.
    """
    return round(1.0 - (l2_distance ** 2) / 2.0, 4)


def hybrid_retriever(index_id: str, k: int, dense_weight: float):
    """Dense + BM25 over the SAME index the caller asked for.

    assignment3_experiments.build_hybrid_retriever() hardcodes chunks_for() and
    load_index(), i.e. always the 1000/150 default index. Calling it with a
    custom index selected would silently return results from a different corpus
    than the one on screen -- a wrong answer, not an error. The assignment
    script is left alone; this is the parameterised twin.
    """
    from langchain_classic.retrievers import EnsembleRetriever
    from langchain_community.retrievers import BM25Retriever

    meta = index_meta(index_id)
    chunks = chunks_for_config(meta["doc_names"], meta["chunk_size"], meta["chunk_overlap"])
    bm25 = BM25Retriever.from_documents(chunks)
    bm25.k = k
    dense = get_vectorstore(index_id).as_retriever(search_kwargs={"k": k})
    return EnsembleRetriever(retrievers=[dense, bm25], weights=[dense_weight, 1 - dense_weight])


def retrieve(
    query: str,
    k: int = 5,
    index_id: str = DEFAULT_INDEX_ID,
    retriever: str = "dense",
    dense_weight: float = 0.5,
) -> dict:
    if retriever == "hybrid":
        # EnsembleRetriever fuses two rankings by reciprocal rank and exposes no
        # comparable score. Reporting None is honest; inventing one is not.
        docs = hybrid_retriever(index_id, k, dense_weight).invoke(query)[:k]
        chunks = [_chunk_payload(doc, rank=i) for i, doc in enumerate(docs, 1)]
    else:
        scored = get_vectorstore(index_id).similarity_search_with_score(query, k=k)
        chunks = [
            _chunk_payload(doc, rank=i, score=_to_similarity(float(distance)))
            for i, (doc, distance) in enumerate(scored, 1)
        ]
    return {
        "query": query,
        "k": k,
        "index_id": index_id,
        "retriever": retriever,
        "dense_weight": dense_weight if retriever == "hybrid" else None,
        "has_scores": retriever != "hybrid",
        "chunks": chunks,
    }


# --- hit-rate: the free metric ----------------------------------------------


def evaluate_retrieval(
    index_id: str = DEFAULT_INDEX_ID,
    k: int = 5,
    retriever: str = "dense",
    dense_weight: float = 0.5,
    report: Callable[[str, int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> dict:
    """hit-rate@K over the answerable eval questions. No judge, no reference
    answer, one boolean per question -- so a config change can be measured
    before a single API call is spent, which is what Task 6 asks for.
    """
    import pandas as pd
    from assignment3_build_eval_set import load_eval_set

    answerable = load_eval_set()
    answerable = answerable[answerable["answerable"]]
    total = len(answerable)
    ensemble = hybrid_retriever(index_id, k, dense_weight) if retriever == "hybrid" else None
    vectorstore = get_vectorstore(index_id)

    rows = []
    for i, (_, row) in enumerate(answerable.iterrows()):
        if should_cancel and should_cancel():
            raise RuntimeError("בוטל על ידי המשתמש.")
        if report:
            report("מודד hit@k", i, total)
        docs = (ensemble.invoke(row["question"])[:k] if ensemble
                else vectorstore.similarity_search(row["question"], k=k))
        rows.append({
            "id": int(row["id"]),
            "difficulty": row["difficulty"],
            **hit_rate_row(
                row["evidence_doc"], row["evidence_page"],
                [d.metadata["doc_name"] for d in docs],
                [_chunk_payload(d)["location"] for d in docs],
            ),
        })
    if report:
        report("מודד hit@k", total, total)

    df = pd.DataFrame(rows)
    easy = df[df["difficulty"] == "easy"]["hit_at_k"]
    hard = df[df["difficulty"] == "hard"]["hit_at_k"]
    return {
        "index_id": index_id,
        "k": k,
        "retriever": retriever,
        "dense_weight": dense_weight if retriever == "hybrid" else None,
        "n": total,
        "hit_at_k": round(float(df["hit_at_k"].mean()), 3),
        "hit_at_k_any_doc": round(float(df["hit_at_k_any_doc"].mean()), 3),
        "hit_at_k_easy": round(float(easy.mean()), 3) if len(easy) else None,
        "hit_at_k_hard": round(float(hard.mean()), 3) if len(hard) else None,
        "misses": [int(r["id"]) for r in rows if not r["hit_at_k"]],
    }


# --- building ---------------------------------------------------------------


def build_index_with_progress(
    doc_names: list[str],
    chunk_size: int,
    chunk_overlap: int,
    embedding_model: str,
    report: Callable[[str, int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> dict:
    """Embed in batches so the progress bar reflects real work.

    FAISS.from_documents() embeds everything in one opaque call; on a few
    hundred Hebrew chunks that is CPU-minutes with nothing to show. Seeding from
    the first batch and add_documents()-ing the rest gives per-batch progress and
    a cancellation point, at no measurable cost -- the index is identical.
    """
    from langchain_community.vectorstores import FAISS

    if embedding_model not in EMBEDDING_MODELS:
        raise ValueError(f"מודל embedding לא מוכר: {embedding_model}")

    def step(phase: str, done: int, total: int) -> None:
        if report:
            report(phase, done, total)

    step("מפרק לצ'אנקים", 0, 1)
    chunks = chunks_for_config(doc_names, chunk_size, chunk_overlap)
    step("מפרק לצ'אנקים", 1, 1)

    index_id = config_slug(doc_names, chunk_size, chunk_overlap, embedding_model)
    target = os.path.join(CUSTOM_INDEX_ROOT, index_id)

    embeddings = PrefixedEmbeddings(embedding_model)
    total = len(chunks)
    batches = [chunks[i:i + EMBED_BATCH_SIZE] for i in range(0, total, EMBED_BATCH_SIZE)]

    step("מחשב embeddings", 0, total)
    vectorstore = FAISS.from_documents(batches[0], embeddings)
    done = len(batches[0])
    step("מחשב embeddings", done, total)

    for batch in batches[1:]:
        if should_cancel and should_cancel():
            raise RuntimeError("בוטל על ידי המשתמש.")
        vectorstore.add_documents(batch)
        done += len(batch)
        step("מחשב embeddings", done, total)

    step("שומר לדיסק", 0, 1)
    os.makedirs(CUSTOM_INDEX_ROOT, exist_ok=True)
    if os.path.isdir(target):
        shutil.rmtree(target)
    vectorstore.save_local(target)

    meta = {
        "index_id": index_id,
        "label": f"{chunk_size}/{chunk_overlap} · {embedding_model.split('/')[-1]}",
        "doc_names": list(doc_names),
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "embedding_model": embedding_model,
        "chunk_count": total,
    }
    with open(os.path.join(target, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)

    _vectorstore_cache[index_id] = vectorstore
    step("שומר לדיסק", 1, 1)
    return {**meta, "read_only": False}
