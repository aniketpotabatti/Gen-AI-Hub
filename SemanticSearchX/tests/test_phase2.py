"""Phase 2 tests: BM25, exact-match, RRF fusion, hybrid retriever, metrics."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dense_retrieval.base import VectorStore
from evaluation.metrics import evaluate
from hybrid_retrieval.fusion import HybridRetriever, reciprocal_rank_fusion
from sparse_retrieval.bm25 import BM25Index
from sparse_retrieval.exact_match import ExactMatchIndex


def _metas(n, **extra):
    return [{"chunk_id": f"c{i}", **extra} for i in range(n)]


def test_bm25_ranks_term_match_first():
    idx = BM25Index()
    idx.add_documents(
        ["the cat sat on the mat", "quantum field theory introduction", "dogs and cats"],
        metadatas=_metas(3),
    )
    ids, scores, metas = idx.search("quantum field theory", k=3)
    assert ids[0] == 1
    assert metas[0]["chunk_id"] == "c1"
    assert scores[0] > 0


def test_bm25_empty_and_filter():
    idx = BM25Index()
    assert idx.search("anything") == ([], [], [])
    idx.add_documents(["apple banana", "cherry pie"], metadatas=_metas(2, source="s"))
    assert idx.search("   ") == ([], [], [])
    assert idx.search("apple", metadata_filter={"source": "nope"}) == ([], [], [])
    ids, _, _ = idx.search("apple", metadata_filter={"source": "s"})
    assert ids == [0]


def test_exact_match_case_insensitive_and_filter():
    idx = ExactMatchIndex()
    idx.add_documents(["Error CODE-42 occurred", "all good here"], metadatas=_metas(2))
    ids, _, _ = idx.search("code-42")
    assert ids == [0]
    assert idx.search("CODE-42", metadata_filter={"chunk_id": "zzz"}) == ([], [], [])


def test_rrf_prefers_consensus():
    # c0 ranked #1 by both lists; c1 ranked #1 once only.
    fused = reciprocal_rank_fusion([[0, 1], [0, 2]], k=60)
    assert fused[0] > fused[1]
    assert fused[0] > fused[2]


def _toy_hybrid():
    """Dense finds c0 only, BM25 finds c1 only -> hybrid returns both."""
    dim = 8
    vs = VectorStore(dimension=dim, use_faiss=False)
    vecs = np.zeros((2, dim), dtype=np.float32)
    vecs[0, 0] = 1.0  # c0 aligns with query direction
    vecs[1, 1] = 1.0  # c1 orthogonal to query
    vs.add_vectors(vecs, metadata=[
        {"chunk_id": "c0", "content": "c0 text"},
        {"chunk_id": "c1", "content": "c1 text"},
    ])
    bm25 = BM25Index()
    bm25.add_documents(
        ["unrelated filler words here", "zebras in the savanna"],
        metadatas=[{"chunk_id": "c0"}, {"chunk_id": "c1"}],
    )
    exact = ExactMatchIndex()
    exact.add_documents(["unrelated filler words here", "zebras in the savanna"],
                        metadatas=[{"chunk_id": "c0"}, {"chunk_id": "c1"}])

    class FakeEmbed:
        def encode(self, texts):
            v = np.zeros((len(texts), dim), dtype=np.float32)
            v[:, 0] = 1.0
            return v

    return HybridRetriever(vs, bm25, exact, FakeEmbed())


def test_hybrid_fuses_dense_and_bm25():
    hy = _toy_hybrid()
    res = hy.search("zebras", k=2, candidate_k=2)
    got = {r["chunk_id"] for r in res}
    assert got == {"c0", "c1"}
    by_id = {r["chunk_id"]: r for r in res}
    assert "dense" in by_id["c0"]["strategies"]
    assert "bm25" in by_id["c1"]["strategies"]
    assert all(r["rrf_score"] > 0 for r in res)


def test_metrics_known_values():
    rankings = {"q1": ["a", "b", "c"]}
    relevance = {"q1": {"b"}}
    out = evaluate(rankings, relevance, ks=[1, 3])
    assert out["recall@1"] == 0.0
    assert out["hit_rate@1"] == 0.0
    assert out["hit_rate@3"] == 1.0
    assert out["recall@3"] == 1.0
    assert out["mrr"] == 0.5
