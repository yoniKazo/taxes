"""X1: MCP server exposing the assignment-3 tax corpus for Claude Code to
query directly during work, instead of Read/Grep on documents that have
grown past a comfortable context size (6 documents, 151 chunks, FAISS index).

Deliberately three narrow tools, not one generic "query the corpus" tool
(per the Implementation Guide: narrow, purpose-named tools beat one that
takes arbitrary input). All three reuse api/rag/retrieval.py rather than
re-implementing index loading -- same canonical FAISS index the API and
CLI scripts use, same L2-to-similarity conversion (CODIFY 2026-08-20).

No generation tool on purpose: answering a question costs a Gemini call
that this server has no way to throttle or account for, and generation
is already exposed as a tested HTTP API (api/rag/generation.py). This
server is the free half only -- retrieval, at 0 LLM calls.

Run: `python mcp_servers/tax_corpus.py` (stdio transport), from tax-copilot/
so the relative sys.path setup in api/rag/__init__.py resolves.
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mcp.server.mcpserver import MCPServer  # noqa: E402

from api.rag import retrieval  # noqa: E402  -- adds src/ to sys.path as a side effect

mcp = MCPServer(
    name="tax_corpus",
    instructions=(
        "Read-only access to the tax-copilot RAG corpus (6 documents, 151 "
        "chunks, canonical FAISS index). Retrieval only -- no generation, "
        "no LLM calls."
    ),
)


@mcp.tool()
def search_tax_corpus(query: str, top_k: int = 5) -> list[dict]:
    """Semantic search over the canonical tax corpus. 0 LLM calls -- local
    embeddings + FAISS only. Returns the top_k most relevant chunks, each
    with its document, location (page or section), similarity score, and
    text."""
    vectorstore = retrieval.get_vectorstore()
    results = vectorstore.similarity_search_with_score(query, k=top_k)
    return [
        retrieval._chunk_payload(doc, rank=i + 1, score=retrieval._to_similarity(l2))
        for i, (doc, l2) in enumerate(results)
    ]


@mcp.tool()
def list_corpus_documents() -> list[dict]:
    """List every document in the tax corpus, from corpus_manifest.json:
    doc_name, topic, format, and source_url for each."""
    return retrieval.build_index.load_manifest()


@mcp.tool()
def get_chunk(doc_name: str, chunk_index: int) -> dict:
    """Fetch one full chunk by (doc_name, chunk_index) -- the same pair
    shown in search_tax_corpus results and in the RAG Lab UI's chunk
    browser. Raises if no such chunk exists."""
    chunks = retrieval.chunks_for_config(doc_names=[doc_name])
    for chunk in chunks:
        if chunk.metadata.get("chunk_index") == chunk_index:
            return retrieval._chunk_payload(chunk)
    raise ValueError(f"no chunk {chunk_index} in document {doc_name!r}")


if __name__ == "__main__":
    mcp.run(transport="stdio")
