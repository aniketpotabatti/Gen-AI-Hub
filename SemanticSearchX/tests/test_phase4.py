"""Phase 4 tests: classifier categories, routing params, adaptive retrieval."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adaptive_router.classifier import classify
from adaptive_router.router import AdaptiveRetriever, route, _split_comparison
from dense_retrieval.base import VectorStore
from hybrid_retrieval.fusion import HybridRetriever
from sparse_retrieval.bm25 import BM25Index
from sparse_retrieval.exact_match import ExactMatchIndex


def test_classifier_categories():
    assert classify("What does CODE-42 mean?")["category"] == "identifier"
    assert classify('search for "exact phrase here"')["category"] == "identifier"
    assert classify("dense vs sparse retrieval, pros and cons")["category"] == "comparison"
    assert classify("what's new in v2.3 changelog")["category"] in ("identifier", "version")
    assert classify("cite evidence with statistics from the study")["category"] == "evidence"
    assert classify("how does machine learning work")["category"] == "conceptual"
    assert classify("")["category"] == "conceptual"
    assert classify("CODE-42")["confidence"] > 0.5


def test_route_params_per_category():
    r = route("CODE-42 failed")
    assert r["category"] == "identifier"
    assert r["rerank"] is False
    assert r["weights"]["exact"] > r["weights"]["dense"]
    r = route("how does embedding work")
    assert r["category"] == "conceptual"
    assert r["rerank"] is True
    r = route("prove it with evidence and cite sources")["category"]
    assert route("prove it with evidence and cite sources")["candidate_k"] == 30
    assert r == "evidence"


def test_split_comparison():
    arms = _split_comparison("dense vs sparse retrieval")
    assert len(arms) == 2
    assert _split_comparison("plain query") == ["plain query"]


def _adaptive_toy():
    dim = 8
    vs = VectorStore(dimension=dim, use_faiss=False)
    vecs = np.zeros((3, dim), dtype=np.float32)
    vecs[:, 0] = 1.0
    vs.add_vectors(vecs, metadata=[
        {"chunk_id": "c0", "content": "dense retrieval explained"},
        {"chunk_id": "c1", "content": "CODE-42 index missing"},
        {"chunk_id": "c2", "content": "sparse retrieval explained"},
    ])
    texts = ["dense retrieval explained with embeddings",
             "CODE-42 means the index file is missing",
             "sparse retrieval explained with inverted index"]
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

    from reranking.cross_encoder import Reranker
    r = Reranker.__new__(Reranker)
    r.model = None
    r.model_name = "heuristic"
    hy = HybridRetriever(vs, bm25, exact, FakeEmbed(), reranker=r)
    return AdaptiveRetriever(hy)


def test_adaptive_identifier_routes_lexical():
    ad = _adaptive_toy()
    out = ad.search("CODE-42", k=2)
    assert out["route"]["category"] == "identifier"
    assert out["results"][0]["chunk_id"] == "c1"
    assert out["results"][0]["route"] == "identifier"


def test_adaptive_comparison_covers_both_arms():
    ad = _adaptive_toy()
    out = ad.search("dense vs sparse retrieval", k=3)
    assert out["route"]["category"] == "comparison"
    got = {r["chunk_id"] for r in out["results"]}
    assert {"c0", "c2"} <= got


def test_adaptive_weights_restored():
    ad = _adaptive_toy()
    before = dict(ad.hybrid.weights)
    ad.search("CODE-42", k=1)
    assert ad.hybrid.weights == before
