"""Phase 6 tests: Quality metrics, System profiler, and Robustness benchmark suite."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.metrics import (
    recall_at_k,
    precision_at_k,
    hit_rate_at_k,
    mrr,
    context_precision_at_k,
    context_recall_at_k,
    evaluate,
)
from evaluation.profiler import (
    measure_latency_and_throughput,
    measure_index_size,
    estimate_costs,
)
from evaluation.robustness import RobustnessBenchmark
from evaluation.benchmark_dataset import build_default_robustness_suite
from tests.test_phase4 import _adaptive_toy


def test_quality_metrics():
    retrieved = ["c1", "c2", "c3", "c4", "c5"]
    relevant = {"c1", "c3"}

    # Precision & Recall
    assert precision_at_k(retrieved, relevant, k=3) == 2 / 3
    assert recall_at_k(retrieved, relevant, k=3) == 1.0
    assert recall_at_k(retrieved, relevant, k=1) == 0.5

    # Hit Rate & MRR
    assert hit_rate_at_k(retrieved, relevant, k=1) == 1.0
    assert mrr(retrieved, relevant) == 1.0
    assert mrr(["c2", "c1"], relevant) == 0.5

    # Context precision (ranks 1 and 3 are relevant: precisions are 1/1 and 2/3)
    # Context precision is (1.0 + 2/3) / 2
    assert context_precision_at_k(retrieved, relevant, k=3) > 0.8
    assert context_recall_at_k(retrieved, relevant, k=3) == 1.0

    # Aggregate evaluate
    rankings = {"q1": retrieved}
    relevance = {"q1": relevant}
    report = evaluate(rankings, relevance, ks=[1, 3, 5])
    assert "recall@3" in report
    assert "precision@3" in report
    assert "context_precision@3" in report
    assert "mrr" in report


def test_profiler_and_cost_modeling():
    # Latency & Throughput
    res = measure_latency_and_throughput(lambda q: time_sim(q), ["q1", "q2", "q3"], warmup=1)
    assert res["total_queries"] == 3
    assert res["p50_ms"] >= 0.0
    assert res["throughput_qps"] > 0.0

    # Index size
    idx_info = measure_index_size(os.path.dirname(__file__))
    assert idx_info["total_bytes"] > 0
    assert idx_info["total_mb"] >= 0.0

    # Cost estimator
    costs = estimate_costs(
        num_queries=1000,
        avg_query_tokens=20,
        num_indexed_chunks=500,
        avg_chunk_tokens=150,
        candidate_depth_k=20,
    )
    assert costs["total_cost_usd"] > 0.0
    assert costs["reranker_cost_usd"] > costs["query_embedding_cost_usd"]


def time_sim(q):
    return len(q)


def test_robustness_benchmark_suite():
    ad = _adaptive_toy()
    suite = build_default_robustness_suite("c0", "c1", "c2")
    bench = RobustnessBenchmark(suite)

    def retriever_fn(query, history=None):
        out = ad.search(query, k=3, conversation_history=history, enable_intelligence=True)
        return [r["chunk_id"] for r in out["results"]]

    results = bench.run(retriever_fn, k=3)
    assert results["total_cases"] == 11
    assert "exact_identifier" in results["categories"]
    assert "multi_turn" in results["categories"]
    assert results["categories"]["exact_identifier"]["avg_recall"] == 1.0
    assert results["unanswerable_handling_rate"] == 1.0
