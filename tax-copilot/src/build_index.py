"""Task 3: parse -> chunk -> enrich -> embed -> store.

Reads assignment3/data/corpus_manifest.json (6 docs: 5 Hebrew markdown guides +
1 official tax-authority PDF), chunks at the assignment's fixed baseline
settings, attaches doc_name/page/section metadata to every chunk (without which
citations and hit-rate are impossible later), and saves a FAISS index to disk.

Run directly to also print 10 random chunks and 3 sanity retrievals -- the
"actually look at it" step the assignment requires before moving on.
"""

import bisect
import json
import os
import random
import re
import sys

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from embeddings import default_embeddings

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
MANIFEST_PATH = os.path.join(SCRIPT_DIR, "..", "assignment3", "data", "corpus_manifest.json")
INDEX_DIR = os.path.join(SCRIPT_DIR, "..", "assignment3", "index")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

SANITY_QUERIES = [
    "מהו שיעור מס היסף?",                              # appears in 3 different docs
    "מהי תקרת הפטור ממס שבח לדירת מגורים יחידה?",       # one clear home: real-estate
    "מהי משכורת קובעת להפרשות לקרן השתלמות?",           # employees guide + the PDF
]

_HEADING_RE = re.compile(r"^#{1,3}[ \t]+(.+)$", re.MULTILINE)


def load_manifest() -> list[dict]:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_raw_documents(manifest: list[dict]) -> list[Document]:
    """One Document per markdown file; one Document per PDF page."""
    docs: list[Document] = []
    for entry in manifest:
        abs_path = os.path.join(REPO_ROOT, entry["path"])
        if entry["format"] == "pdf":
            loaded = PyPDFLoader(abs_path).load()
        else:
            loaded = TextLoader(abs_path, encoding="utf-8").load()
        for doc in loaded:
            doc.metadata["doc_name"] = entry["doc_name"]
            doc.metadata["doc_format"] = entry["format"]
            doc.metadata["topic"] = entry["topic"]
            doc.metadata["source_url"] = entry["source_url"]
            doc.metadata["language"] = "he"
            # PyPDFLoader pages are 0-indexed; humans (and the eval set) count from 1.
            if entry["format"] == "pdf":
                doc.metadata["page"] = int(doc.metadata.get("page", 0)) + 1
            else:
                doc.metadata["page"] = None
        docs.extend(loaded)
    return docs


def split_documents(
    raw_docs: list[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    """Shared by assignment3_generate_eval.py and the Task 6 chunk-size sweep."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, add_start_index=True
    )
    return splitter.split_documents(raw_docs)


def enrich_section_metadata(chunks: list[Document], manifest: list[dict]) -> None:
    """Attach the nearest preceding markdown heading to every md-origin chunk.

    PDF chunks already carry a real page number and get section=None.
    """
    headings_by_doc: dict[str, tuple[list[int], list[str]]] = {}
    for entry in manifest:
        if entry["format"] != "md":
            continue
        with open(os.path.join(REPO_ROOT, entry["path"]), "r", encoding="utf-8") as f:
            text = f.read()
        matches = list(_HEADING_RE.finditer(text))
        headings_by_doc[entry["doc_name"]] = (
            [m.start() for m in matches],
            [m.group(1).strip() for m in matches],
        )

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i
        entry = headings_by_doc.get(chunk.metadata["doc_name"])
        if entry is None:
            chunk.metadata["section"] = None
            continue
        offsets, titles = entry
        pos = bisect.bisect_right(offsets, chunk.metadata.get("start_index", 0)) - 1
        chunk.metadata["section"] = titles[pos] if pos >= 0 else None


def build_chunks() -> tuple[list[Document], list[dict]]:
    manifest = load_manifest()
    raw_docs = load_raw_documents(manifest)
    chunks = split_documents(raw_docs)
    enrich_section_metadata(chunks, manifest)
    return chunks, manifest


def build_and_save_index(
    chunks: list[Document], embeddings: Embeddings | None = None, index_dir: str = INDEX_DIR
) -> FAISS:
    vectorstore = FAISS.from_documents(chunks, embeddings or default_embeddings())
    vectorstore.save_local(index_dir)
    return vectorstore


def load_index(embeddings: Embeddings | None = None, index_dir: str = INDEX_DIR) -> FAISS:
    return FAISS.load_local(
        index_dir, embeddings or default_embeddings(), allow_dangerous_deserialization=True
    )


def _describe(chunk: Document) -> str:
    md = chunk.metadata
    where = f"עמוד {md['page']}" if md.get("page") else f"סעיף: {md.get('section')}"
    return f"{md['doc_name']} | {where}"


def print_random_chunks(chunks: list[Document], n: int = 10, seed: int = 20260818) -> None:
    print(f"\n{'=' * 70}\n10 צ'אנקים אקראיים (Task 3 -- 'actually look at it')\n{'=' * 70}")
    for chunk in random.Random(seed).sample(chunks, n):
        print(f"\n--- {_describe(chunk)} (len={len(chunk.page_content)}) ---")
        print(chunk.page_content)


def sanity_queries(vectorstore: FAISS, k: int = 3) -> None:
    print(f"\n{'=' * 70}\n3 שאילתות sanity דרך similarity_search\n{'=' * 70}")
    for query in SANITY_QUERIES:
        print(f"\n### {query}")
        for rank, chunk in enumerate(vectorstore.similarity_search(query, k=k), 1):
            preview = chunk.page_content[:200].replace("\n", " ")
            print(f"  [{rank}] {_describe(chunk)}\n      {preview}")


if __name__ == "__main__":
    chunks, manifest = build_chunks()
    print(f"{len(manifest)} מסמכים -> {len(chunks)} צ'אנקים")
    by_doc: dict[str, int] = {}
    for chunk in chunks:
        by_doc[chunk.metadata["doc_name"]] = by_doc.get(chunk.metadata["doc_name"], 0) + 1
    for doc_name, count in by_doc.items():
        print(f"  {doc_name}: {count}")

    vectorstore = build_and_save_index(chunks)
    print(f"\nאינדקס נשמר ב-{os.path.abspath(INDEX_DIR)}")

    print_random_chunks(chunks)
    sanity_queries(vectorstore)
