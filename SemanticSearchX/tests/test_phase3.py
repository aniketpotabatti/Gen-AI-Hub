"""Phase 3 tests: normalization, reranker, hybrid rerank stage, depth tuning."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dense_retrieval.base import VectorStore
from evaluation.metrics import evaluate
from hybrid_retrieval.fusion import HybridRetriever
from reranking.cross_encoder import Reranker
from reranking.normalize import minmax, zscore
from sparse_retrieval.bm25 import BM25Index
from sparse_retrieval.exact_match import ExactMatchIndex


def test_minmax_basic_and_edge():
    assert minmax([1.0, 2.0, 3.0]) == [0.0, 0.5, 1.0]
    assert minmax([]) == []
    assert minmax([5.0, 5.0]) == [0.0, 0.0]


def test_zscore_basic_and_constant():
    out = zscore([1.0, 2.0, 3.0])
    assert abs(sum(out)) < 1e-9
    assert out[0] < out[1] < out[2]
    assert zscore([]) == []
    assert zscore([4.0, 4.0]) == [0.0, 0.0]


def test_heuristic_reranker_prefers_overlap():
    r = Reranker.__new__(Reranker)
    r.model = None
    texts = ["unrelated filler about cooking", "CODE-42 means the index file is missing"]
    scores = r.score("what does CODE-42 mean", texts)
    assert scores[1] > scores[0]
    assert r.score("q", []) == []
    order, top = r.rerank("CODE-42", texts, top_k=1)
    fresh = r.score("CODE-42", texts)
    assert order == [1]
    assert top == [fresh[1]]


def _rerank_toy():
    dim = 8
    vs = VectorStore(dimension=dim, use_faiss=False)
    vecs = np.zeros((3, dim), dtype=np.float32)
    vecs[0, 0] = 1.0  # dense top: irrelevant
    vecs[1, 0] = 0.9
    vecs[2, 1] = 1.0
    vs.add_vectors(vecs, metadata=[
        {"chunk_id": "c0", "content": "c0 preview"},
        {"chunk_id": "c1", "content": "c1 preview"},
        {"chunk_id": "c2", "content": "c2 preview"},
    ])
    texts = ["weather forecast sunny skies", "weather forecast sunny skies",
             "CODE-42 means the index file is missing"]
    metas = [{"chunk_id": "c0"}, {"chunk_id": "c1"}, {"chunk_id": "c2"}]
    bm25 = BM25Index()
    bm25.add_documents(texts, metadatas=metas)
    exact = ExactMatchIndex()
    exact.add_documents(texts, metadatas=metas)

    class FakeEmbed:
        def encode(self, texts):
            v = np.zeros((len(texts), dim), dtype=np.float32)
            v[:, 0] = 1.0
            return v

    r = Reranker.__new__(Reranker)
    r.model = None
    r.model_name = "heuristic"
    return HybridRetriever(vs, bm25, exact, FakeEmbed(), reranker=r)


def test_hybrid_rerank_promotes_lexical_match():
    hy = _rerank_toy()
    base = hy.search("CODE-42", k=1, candidate_k=3)
    assert base[0]["reranker_score"] == 0.0
    assert "rerank" not in base[0]["strategies"]
    top = hy.search("CODE-42", k=1, candidate_k=3, rerank=True)
    assert top[0]["chunk_id"] == "c2"
    assert top[0]["reranker_score"] > 0
    assert 0.0 <= top[0]["reranker_norm"] <= 1.0
    assert "rerank" in top[0]["strategies"]


def test_candidate_depth_monotonic_recall():
    # Wider candidate pool should not reduce hybrid+rerank recall here.
    hy = _rerank_toy()
    relevance = {"q": {"c2"}}
    recalls = []
    for depth in (1, 2, 3):
        rank = {"q": [r["chunk_id"] for r in hy.search("CODE-42", k=3,
                                                       candidate_k=depth, rerank=True)]}
        recalls.append(evaluate(rank, relevance, ks=[3])["recall@3"])
    assert recalls == sorted(recalls)
    assert recalls[-1] == 1.0
