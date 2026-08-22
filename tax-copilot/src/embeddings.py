"""LangChain Embeddings wrapper around a local sentence-transformers model.

Hand-rolled rather than using HuggingFaceBgeEmbeddings so the asymmetric prefix
rule stays visible in this file: bge prefixes the QUERY only and leaves indexed
passages bare, while e5 prefixes both sides with different strings. Getting
either wrong does not crash -- it just quietly degrades retrieval.

The assignment pins bge-small-en-v1.5, but Task 3's sanity retrievals showed it
cannot rank this Hebrew corpus (hit-rate@1 = 1/6, and every query returned the
same chunk). e5 is therefore the operating default; bge is kept because Task 6
re-measures it as a documented experiment. See assignment3_writeup.md.
"""

import sys
from typing import ClassVar

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

sys.stdout.reconfigure(encoding="utf-8")

BGE_MODEL = "BAAI/bge-small-en-v1.5"
E5_MODEL = "intfloat/multilingual-e5-small"

# Per each model card. bge: query prefix only, passages bare.
# e5: BOTH sides prefixed, but with different prefixes.
_PREFIXES: dict[str, tuple[str, str]] = {
    # model_name: (query_prefix, passage_prefix)
    BGE_MODEL: ("Represent this sentence for searching relevant passages: ", ""),
    E5_MODEL: ("query: ", "passage: "),
}


class PrefixedEmbeddings(Embeddings):
    """SentenceTransformer + the model card's query/passage prefix convention."""

    _cache: ClassVar[dict[str, SentenceTransformer]] = {}

    def __init__(self, model_name: str = BGE_MODEL):
        if model_name not in _PREFIXES:
            raise ValueError(f"no prefix convention recorded for {model_name!r} -- read its model card first")
        self.model_name = model_name
        self.query_prefix, self.passage_prefix = _PREFIXES[model_name]
        if model_name not in PrefixedEmbeddings._cache:
            PrefixedEmbeddings._cache[model_name] = SentenceTransformer(model_name)
        self.model = PrefixedEmbeddings._cache[model_name]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        prefixed = [self.passage_prefix + t for t in texts]
        # normalize_embeddings=True matters: these models are trained for cosine
        # similarity, and FAISS's default IndexFlatL2 ranks identically to cosine
        # only when the vectors are unit length (L2^2 = 2 - 2*cos).
        return self.model.encode(prefixed, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode(self.query_prefix + text, normalize_embeddings=True).tolist()


DEFAULT_MODEL = E5_MODEL


def bge_embeddings() -> PrefixedEmbeddings:
    return PrefixedEmbeddings(BGE_MODEL)


def e5_embeddings() -> PrefixedEmbeddings:
    return PrefixedEmbeddings(E5_MODEL)


def default_embeddings() -> PrefixedEmbeddings:
    return PrefixedEmbeddings(DEFAULT_MODEL)
