"""Tests for Phase 7: Retrieval Explainability."""
from evaluation.explainability import RetrievalExplainer
from tests.test_phase4 import _adaptive_toy


def test_explainer_single_result_breakdown():
    explainer = RetrievalExplainer()
    sample_result = {
        "chunk_id": "c1",
        "rrf_score": 0.033,
        "dense_score": 0.88,
        "bm25_score": 2.45,
        "exact_score": 1.0,
        "reranker_score": 0.95,
        "reranker_norm": 0.95,
        "strategies": ["dense", "bm25", "exact", "rerank"],
        "metadata": {"chunk_id": "c1", "source": "incident_log.txt", "content": "error code CODE-42"},
    }

    exp = explainer.explain_result("What causes CODE-42?", sample_result)

    # 1. Final score
    assert "final_score" in exp
    assert exp["final_score"] == 0.95

    # 2. Dense score
    assert exp["dense_score"] == 0.88

    # 3. Sparse score breakdown
    assert "sparse_score" in exp
    assert exp["sparse_score"]["bm25_score"] == 2.45
    assert exp["sparse_score"]["exact_score"] == 1.0
    assert exp["sparse_score"]["combined_sparse_score"] == 3.45

    # 4. Reranker score
    assert exp["reranker_score"]["raw"] == 0.95
    assert exp["reranker_score"]["normalized"] == 0.95

    # 5. Retrieval strategy
    assert exp["retrieval_strategy"] == ["dense", "bm25", "exact", "rerank"]

    # 6. Matching signals
    signals = exp["matching_signals"]
    assert any(s["type"] == "exact_code_match" and s["term"] == "CODE-42" for s in signals)
    assert any(s["type"] == "semantic_similarity" for s in signals)
    assert any(s["type"] == "cross_encoder_rerank" for s in signals)

    # 7. Source document & chunk metadata
    assert exp["source_document"] == "incident_log.txt"
    assert exp["chunk_metadata"]["chunk_id"] == "c1"
    assert "narrative" in exp
    assert "CODE-42" in exp["narrative"]


def test_adaptive_retriever_explain_flag():
    adaptive = _adaptive_toy()
    out = adaptive.search("investigate CODE-42 failure", k=2, explain=True)

    assert "explanations" in out
    assert len(out["explanations"]) == len(out["results"])

    first_exp = out["explanations"][0]
    assert first_exp["chunk_id"] == "c1"
    assert "final_score" in first_exp
    assert "dense_score" in first_exp
    assert "sparse_score" in first_exp
    assert "reranker_score" in first_exp
    assert "retrieval_strategy" in first_exp
    assert "matching_signals" in first_exp
    assert "chunk_metadata" in first_exp

    # Check signal extraction for identifier query
    signal_types = [s["type"] for s in first_exp["matching_signals"]]
    assert "exact_code_match" in signal_types or "term_overlap" in signal_types


def test_explain_without_rerank():
    explainer = RetrievalExplainer()
    result = {
        "chunk_id": "c2",
        "rrf_score": 0.016,
        "dense_score": 0.72,
        "bm25_score": 1.2,
        "exact_score": 0.0,
        "reranker_score": 0.0,
        "reranker_norm": 0.0,
        "strategies": ["dense", "bm25"],
        "metadata": {"chunk_id": "c2", "source": "ml_guide.txt", "content": "deep learning guide"},
    }

    exp = explainer.explain_result("deep learning overview", result)
    assert exp["final_score"] == 0.016
    assert exp["reranker_score"]["raw"] == 0.0
    assert exp["retrieval_strategy"] == ["dense", "bm25"]
    assert exp["source_document"] == "ml_guide.txt"
