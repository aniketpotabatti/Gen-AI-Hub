"""Package init for observability."""
from observability.logging import setup_logging
from observability.metrics import (
    SEARCH_REQUEST_TOTAL,
    SEARCH_LATENCY_SECONDS,
    INDEXED_CHUNKS_TOTAL,
    CACHE_OPERATIONS_TOTAL,
    FAILURE_DIAGNOSES_TOTAL,
    ARENA_RUNS_TOTAL,
    ARENA_PIPELINE_SCORE,
    get_latest_metrics,
    CONTENT_TYPE_LATEST,
)
from observability.tracing import get_tracer, trace_span

__all__ = [
    "setup_logging",
    "SEARCH_REQUEST_TOTAL",
    "SEARCH_LATENCY_SECONDS",
    "INDEXED_CHUNKS_TOTAL",
    "CACHE_OPERATIONS_TOTAL",
    "FAILURE_DIAGNOSES_TOTAL",
    "ARENA_RUNS_TOTAL",
    "ARENA_PIPELINE_SCORE",
    "get_latest_metrics",
    "CONTENT_TYPE_LATEST",
    "get_tracer",
    "trace_span",
]
