"""Prometheus metrics collector for SemanticSearchX."""
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# Search & Retrieval Metrics
SEARCH_REQUEST_TOTAL = Counter(
    "semanticsearchx_search_requests_total",
    "Total search requests processed",
    ["status", "strategy", "cache_hit"],
)

SEARCH_LATENCY_SECONDS = Histogram(
    "semanticsearchx_search_latency_seconds",
    "End-to-end search request latency in seconds",
    ["strategy"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

INDEXED_CHUNKS_TOTAL = Gauge(
    "semanticsearchx_indexed_chunks_total",
    "Total number of chunks indexed in retrieval store",
)

CACHE_OPERATIONS_TOTAL = Counter(
    "semanticsearchx_cache_operations_total",
    "Total cache lookups",
    ["operation", "result"],
)

FAILURE_DIAGNOSES_TOTAL = Counter(
    "semanticsearchx_failure_diagnoses_total",
    "Diagnosed retrieval failures by category",
    ["category"],
)

# Retrieval Benchmark Arena Metrics
ARENA_RUNS_TOTAL = Counter(
    "semanticsearchx_arena_runs_total",
    "Benchmark arena runs executed",
    ["status"],
)

ARENA_PIPELINE_SCORE = Gauge(
    "semanticsearchx_arena_pipeline_score",
    "Score of the most recent arena run per pipeline and metric",
    ["pipeline", "metric"],
)


def get_latest_metrics() -> bytes:
    """Generate serialized Prometheus metrics."""
    return generate_latest()
