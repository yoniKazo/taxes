"""Tests for the free half of the RAG lab: artifacts, retrieval, indexing.

No network and no GEMINI_API_KEY. That is the point of splitting api/rag/ by
cost -- generation.py is the only module that can spend quota, and nothing here
imports it, so the suite cannot start costing money by accident.

The numbers asserted below are the ones the write-up reports. If a refactor
changes them, either the refactor is wrong or the write-up is, and a green test
suite should not be able to hide which.
"""

import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from api.rag import artifacts, retrieval  # noqa: E402

client = TestClient(app)


# --- artifacts: the assignment's own gates ----------------------------------


def test_eval_set_meets_the_assignments_structural_requirements():
    data = artifacts.eval_set()
    assert data["size_ok"], "Task 2 requires 25-40 questions"
    assert data["hard_ok"], "Task 2 requires at least 6 hand-written hard questions"
    for row in data["coverage"]:
        assert row["ok"], f"missing hard-question category: {row['category']}"


def test_baseline_reports_partial_as_its_own_bucket():
    """The raw CSV collapses every non-good verdict into "hallucinated".

    reclassify_baseline() splits `partial` back out; if the merge ever picks up
    the original column again the hallucination count jumps from 3 to 4.
    """
    buckets = artifacts.baseline()["buckets"]
    assert buckets == {"refused": 20, "correct": 10, "partial": 1, "hallucinated": 3}


def test_incomplete_experiments_are_reported_as_incomplete():
    """exp1 was judged for 6 of 34 rows and exp3 never ran.

    Presenting a 6-row mean beside a 34-row baseline would be the exact failure
    the assignment penalises, so status must survive to the API.
    """
    by_name = {e["name"]: e for e in artifacts.experiments_summary()["experiments"]}
    assert by_name["exp1_top_k_8"]["status"] == "partial"
    assert by_name["exp1_top_k_8"]["metrics"] is None
    assert by_name["exp3_hybrid_bm25"]["status"] == "missing"


def test_analysis_reports_empty_broken_pipeline_case_as_a_finding():
    """Task 5(b) found no rows, and that absence is itself the result -- hit@k
    left only one missed retrieval, and on it the system refused."""
    data = artifacts.analysis()
    assert data["right_answer_broken_pipeline"] == []
    assert data["right_answer_broken_pipeline_is_empty"] is True
    assert len(data["worst_rows"]) == 5


# --- chunking ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("chunk_size", "overlap", "expected"),
    [(500, 100, 306), (1000, 150, 151), (1500, 200, 105)],
)
def test_preview_reproduces_the_sweep_chunk_counts(chunk_size, overlap, expected):
    """The counts recorded in task6_sweeps.csv, recomputed with no embedding."""
    assert retrieval.preview_chunks(None, chunk_size, overlap)["chunk_count"] == expected


def test_empty_document_selection_is_an_error_not_the_whole_corpus():
    """None means the whole corpus; [] means the user unticked everything.

    Treating them the same would quietly index all six documents when the user
    asked for none.
    """
    with pytest.raises(ValueError):
        retrieval.chunks_for_config([], 1000, 150)
    assert len(retrieval.chunks_for_config(None, 1000, 150)) == 151


# --- retrieval --------------------------------------------------------------


def test_sanity_queries_still_retrieve_their_documented_documents():
    """Task 3's three probes, with the answers the write-up recorded.

    This is the regression test for retrieval quality itself: it is what would
    fail if the embedding model, the prefix convention, or the index were
    swapped for something that cannot rank Hebrew.
    """
    expected = {
        "מהו שיעור מס היסף?": "employees-tax-guide",
        "מהי תקרת הפטור ממס שבח לדירת מגורים יחידה?": "real-estate-tax-guide",
        "מהי משכורת קובעת להפרשות לקרן השתלמות?": "employees-tax-guide",
    }
    for query, doc_name in expected.items():
        docs = [c["doc_name"] for c in retrieval.retrieve(query, k=5)["chunks"]]
        assert doc_name in docs, f"{query!r} no longer retrieves {doc_name}"


def test_similarity_score_decreases_with_rank():
    """FAISS returns an L2 DISTANCE, where lower is better.

    Without _to_similarity()'s conversion the numbers ascend, and a UI meter
    bound to them draws the best-matching chunk as the emptiest bar.
    """
    scores = [c["score"] for c in retrieval.retrieve("מהו שיעור מס היסף?", k=5)["chunks"]]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_hybrid_reports_no_score_rather_than_a_fake_one():
    """EnsembleRetriever fuses two rankings and exposes no comparable score."""
    result = retrieval.retrieve("סעיף 49א", k=3, retriever="hybrid", dense_weight=0.3)
    assert result["has_scores"] is False
    assert all(c["score"] is None for c in result["chunks"])


# --- hit-rate ---------------------------------------------------------------


def test_hit_rate_reproduces_the_recorded_sweep_for_k5_and_k8():
    """task6_sweeps.csv: k=5 -> 0.969, k=8 -> 1.000, both over 32 questions.

    Slow (64 embedded queries) but free, and it is the number every Task 6
    decision was calibrated against.
    """
    assert retrieval.evaluate_retrieval(k=5)["hit_at_k"] == 0.969
    result = retrieval.evaluate_retrieval(k=8)
    assert result["hit_at_k"] == 1.0
    assert result["n"] == 32


# --- index lifecycle --------------------------------------------------------


def test_building_a_custom_index_leaves_the_graded_index_untouched(tmp_path, monkeypatch):
    """Every assignment3_*.py script loads assignment3/index/. A rebuild
    triggered from the UI must never be able to land there."""
    monkeypatch.setattr(retrieval, "CUSTOM_INDEX_ROOT", str(tmp_path))
    canonical = Path(retrieval.DEFAULT_INDEX_DIR)
    before = {f.name: f.stat().st_mtime for f in canonical.iterdir()}

    progress = []
    meta = retrieval.build_index_with_progress(
        ["employees-tax-guide"], 1000, 150, retrieval.E5_MODEL,
        report=lambda phase, done, total: progress.append((phase, done, total)),
    )

    assert {f.name: f.stat().st_mtime for f in canonical.iterdir()} == before
    assert os.path.isdir(os.path.join(tmp_path, meta["index_id"]))
    assert meta["chunk_count"] == 14

    embed_steps = [p for p in progress if p[0] == "מחשב embeddings"]
    assert [p[1] for p in embed_steps] == sorted(p[1] for p in embed_steps)
    assert embed_steps[-1][1] == embed_steps[-1][2] == meta["chunk_count"]


def test_the_graded_index_cannot_be_deleted():
    with pytest.raises(retrieval.ReadOnlyIndex):
        retrieval.delete_index(retrieval.DEFAULT_INDEX_ID)
    assert client.delete("/rag/indexes/default").status_code == 400
    assert client.delete("/rag/indexes/does-not-exist").status_code == 404


# --- routes -----------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/rag/corpus", "/rag/eval-set", "/rag/baseline", "/rag/metrics",
     "/rag/per-question", "/rag/analysis", "/rag/sweeps", "/rag/experiments",
     "/rag/indexes"],
)
def test_free_routes_return_json(path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.json()


def test_retrieve_route_round_trips_enough_metadata_to_cite_and_reselect():
    """The client sends these chunks back on the manual-selection path, so
    anything missing here cannot be cited or re-used as context."""
    chunk = client.post(
        "/rag/retrieve", json={"query": "מהו שיעור מס היסף?", "k": 3}
    ).json()["chunks"][0]
    for field in ("rank", "score", "doc_name", "location", "text", "chunk_index"):
        assert field in chunk
    assert chunk["text"]


# --- citation guard ----------------------------------------------------------


@pytest.mark.parametrize(
    ("answer", "supplied", "expected"),
    [
        ("שיעור המס הוא 25% [2].", 5, []),
        # The grouped form. A `\[(\d+)\]` pattern matches neither the group nor
        # the numbers in it, so [8] out of 5 chunks passed the guard silently --
        # observed live in the web UI, which is what prompted this test.
        ("מס נוסף בשיעור 3% [1, 2, 8].", 5, [8]),
        ("לפי [1,2] וגם [7].", 5, [7]),
        ("טווח [0] אינו חוקי.", 5, [0]),
        # A bracketed year in the corpus text must not read as a citation, but a
        # bracketed number out of range still must.
        ("התשמ\"ז [1986] קובע.", 5, [1986]),
    ],
)
def test_citation_guard_catches_grouped_citations(answer, supplied, expected):
    import re

    from rag_pipeline import CITATION_RE

    cited = {int(n) for group in CITATION_RE.findall(answer) for n in re.findall(r"\d+", group)}
    assert sorted(n for n in cited if n < 1 or n > supplied) == expected
