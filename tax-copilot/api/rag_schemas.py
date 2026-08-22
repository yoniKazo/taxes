"""Request models for api/routes/rag.py.

Responses are plain dicts assembled in api/rag/*.py rather than Pydantic models:
those payloads are wide (the judged spreadsheet alone is 47 columns) and mirror
files on disk, so pinning a response_model here would mean restating the
assignment's schema in a second place and keeping the two in sync by hand.
Requests are validated -- that is where bad input actually arrives.
"""

from typing import Literal

from pydantic import BaseModel, Field

from api.rag.retrieval import DEFAULT_INDEX_ID, E5_MODEL

RetrieverKind = Literal["dense", "hybrid"]


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=20)
    index_id: str = DEFAULT_INDEX_ID
    retriever: RetrieverKind = "dense"
    dense_weight: float = Field(default=0.5, ge=0.0, le=1.0)


class ChunkIn(BaseModel):
    """A chunk the client is sending back to be used as context.

    The text round-trips through the browser rather than being re-fetched by
    index, because the whole point of manual selection is that the context is
    exactly what the user saw on screen.
    """

    text: str
    doc_name: str | None = None
    page: int | None = None
    section: str | None = None
    chunk_index: int | None = None


class AnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    index_id: str = DEFAULT_INDEX_ID
    k: int = Field(default=5, ge=1, le=20)
    retriever: RetrieverKind = "dense"
    dense_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    # None = retrieve now. A list (including an empty one) = use exactly these:
    # a grounded system handed no context must refuse, and watching that happen
    # is a legitimate thing to want to try.
    chunks: list[ChunkIn] | None = None


class JudgeRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    chunks: list[str] = []
    reference_answer: str | None = None
    answerable: bool | None = None
    answered: bool | None = None


class PreviewRequest(BaseModel):
    doc_names: list[str] | None = None
    chunk_size: int = Field(default=1000, ge=100, le=4000)
    chunk_overlap: int = Field(default=150, ge=0, le=1000)


class BuildIndexRequest(BaseModel):
    doc_names: list[str] = Field(min_length=1)
    chunk_size: int = Field(default=1000, ge=100, le=4000)
    chunk_overlap: int = Field(default=150, ge=0, le=1000)
    embedding_model: str = E5_MODEL


class EvaluateRetrievalRequest(BaseModel):
    index_id: str = DEFAULT_INDEX_ID
    k: int = Field(default=5, ge=1, le=20)
    retriever: RetrieverKind = "dense"
    dense_weight: float = Field(default=0.5, ge=0.0, le=1.0)
