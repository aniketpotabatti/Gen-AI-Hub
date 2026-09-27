"""System performance, resource profiler, and cost modeling for retrieval.

Measures:
- Latency (p50, p95, p99, mean)
- Throughput (queries per second)
- Memory usage (RSS delta)
- Index size on disk
- Embedding cost estimator
- Reranking cost estimator
"""
import os
import time
from typing import Any, Callable, Dict, List, Optional


def measure_latency_and_throughput(
    query_fn: Callable[[str], Any],
    queries: List[str],
    warmup: int = 2,
) -> Dict[str, float]:
    """Profile latency distribution and queries-per-second (QPS)."""
    if not queries:
        return {
            "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0,
            "mean_ms": 0.0, "throughput_qps": 0.0, "total_queries": 0,
        }

    # Warmup runs
    for q in queries[:warmup]:
        query_fn(q)

    latencies_ms: List[float] = []
    total_start = time.perf_counter()

    for q in queries:
        t0 = time.perf_counter()
        query_fn(q)
        lat = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(lat)

    total_time = time.perf_counter() - total_start
    latencies_ms.sort()
    n = len(latencies_ms)

    def percentile(p: float) -> float:
        idx = int(math.ceil(p / 100.0 * n)) - 1
        return latencies_ms[max(0, min(idx, n - 1))]

    import math
    return {
        "p50_ms": percentile(50.0),
        "p95_ms": percentile(95.0),
        "p99_ms": percentile(99.0),
        "mean_ms": sum(latencies_ms) / n,
        "throughput_qps": n / total_time if total_time > 0 else 0.0,
        "total_queries": n,
    }


def measure_index_size(index_dir: str) -> Dict[str, Any]:
    """Calculate the total and per-file storage footprint of the vector/lexical index."""
    if not os.path.exists(index_dir):
        return {"total_bytes": 0, "total_mb": 0.0, "files": {}}

    total_bytes = 0
    file_map = {}
    for root, _, files in os.walk(index_dir):
        for f in files:
            path = os.path.join(root, f)
            sz = os.path.getsize(path)
            total_bytes += sz
            rel = os.path.relpath(path, index_dir)
            file_map[rel] = sz

    return {
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 3),
        "files": file_map,
    }


def estimate_costs(
    num_queries: int,
    avg_query_tokens: int = 15,
    num_indexed_chunks: int = 100,
    avg_chunk_tokens: int = 200,
    candidate_depth_k: int = 20,
    embedding_cost_per_1k_tokens: float = 0.00002,  # e.g., text-embedding-3-small
    reranker_cost_per_1k_tokens: float = 0.002,     # e.g., cross-encoder or Cohere rerank
) -> Dict[str, float]:
    """Model token footprint and estimated USD costs for embedding & reranking."""
    indexing_tokens = num_indexed_chunks * avg_chunk_tokens
    indexing_embedding_cost = (indexing_tokens / 1000.0) * embedding_cost_per_1k_tokens

    query_embedding_tokens = num_queries * avg_query_tokens
    query_embedding_cost = (query_embedding_tokens / 1000.0) * embedding_cost_per_1k_tokens

    # Reranking evaluates (query + chunk) pairs for candidate_depth_k candidates per query
    reranker_tokens_per_query = candidate_depth_k * (avg_query_tokens + avg_chunk_tokens)
    total_reranker_tokens = num_queries * reranker_tokens_per_query
    reranker_cost = (total_reranker_tokens / 1000.0) * reranker_cost_per_1k_tokens

    total_cost = indexing_embedding_cost + query_embedding_cost + reranker_cost

    return {
        "indexing_tokens": indexing_tokens,
        "indexing_embedding_cost_usd": round(indexing_embedding_cost, 6),
        "query_embedding_tokens": query_embedding_tokens,
        "query_embedding_cost_usd": round(query_embedding_cost, 6),
        "total_reranker_tokens": total_reranker_tokens,
        "reranker_cost_usd": round(reranker_cost, 6),
        "total_cost_usd": round(total_cost, 6),
    }
