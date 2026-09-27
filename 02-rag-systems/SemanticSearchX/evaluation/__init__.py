"""Init for evaluation package."""
from evaluation.metrics import (
    recall_at_k,
    precision_at_k,
    hit_rate_at_k,
    mrr,
    ndcg_at_k,
    context_precision_at_k,
    context_recall_at_k,
    evaluate,
)
from evaluation.profiler import (
    measure_latency_and_throughput,
    measure_index_size,
    estimate_costs,
)
from evaluation.robustness import RobustnessBenchmark, RobustnessTestCase
from evaluation.benchmark_dataset import build_default_robustness_suite
from evaluation.explainability import RetrievalExplainer
from evaluation.arena import (
    ArenaQuery,
    CountingReranker,
    RetrievalArena,
    PIPELINE_ORDER,
    PIPELINE_LABELS,
    build_arena_queries_from_test_cases,
    build_self_labeled_queries,
    render_dashboard,
    render_leaderboard,
    to_json,
)

__all__ = [
    "recall_at_k",
    "precision_at_k",
    "hit_rate_at_k",
    "mrr",
    "ndcg_at_k",
    "context_precision_at_k",
    "context_recall_at_k",
    "evaluate",
    "measure_latency_and_throughput",
    "measure_index_size",
    "estimate_costs",
    "RobustnessBenchmark",
    "RobustnessTestCase",
    "build_default_robustness_suite",
    "RetrievalExplainer",
    "ArenaQuery",
    "CountingReranker",
    "RetrievalArena",
    "PIPELINE_ORDER",
    "PIPELINE_LABELS",
    "build_arena_queries_from_test_cases",
    "build_self_labeled_queries",
    "render_dashboard",
    "render_leaderboard",
    "to_json",
]

