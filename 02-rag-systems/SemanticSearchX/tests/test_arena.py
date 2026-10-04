"""Unit and integration tests for the Retrieval Benchmark Arena (plan Phase 6 / dashboard)."""
import json

import httpx
import numpy as np
import pytest

from evaluation.arena import (
    ArenaQuery,
    CountingReranker,
    PIPELINE_LABELS,
    PIPELINE_ORDER,
    RetrievalArena,
    build_arena_queries_from_test_cases,
    build_self_labeled_queries,
    render_dashboard,
    render_leaderboard,
    to_json,
)
from evaluation.benchmark_dataset import build_default_robustness_suite

CORPUS = [
    ("arena_c1", "Machine learning models learn statistical patterns from training data."),
    ("arena_c2", "CODE-42 means the vector index file is missing on disk."),
    ("arena_c3", "Redis multi-tier caching returns repeated retrieval queries in sub-millisecond time."),
    ("arena_c4", "Deep learning uses neural networks with many stacked layers."),
]
METADATAS = [
    {"chunk_id": cid, "content": text, "source": "arena.txt"} for cid, text in CORPUS
]


@pytest.fixture(scope="module")
def engines():
    """Tiny in-memory engine pair (hybrid + adaptive) reused across arena tests."""
    from embeddings.base import EmbeddingModel
    from dense_retrieval.base import VectorStore
    from sparse_retrieval.bm25 import BM25Index
    from sparse_retrieval.exact_match import ExactMatchIndex
    from hybrid_retrieval.fusion import HybridRetriever
    from adaptive_router.router import AdaptiveRetriever
    from reranking.cross_encoder import Reranker

    texts = [text for _, text in CORPUS]
    embed_model = EmbeddingModel()
    embeddings = np.ascontiguousarray(embed_model.encode(texts), dtype=np.float32)
    hybrid = HybridRetriever(
        VectorStore(dimension=embed_model.get_dimension()),
        BM25Index(),
        ExactMatchIndex(),
        embed_model,
        reranker=Reranker(),
    )
    hybrid.index_chunks(texts, METADATAS, embeddings)
    return hybrid, AdaptiveRetriever(hybrid)


@pytest.fixture(scope="module")
def arena(engines):
    hybrid, adaptive = engines
    return RetrievalArena(hybrid, adaptive=adaptive, reranker=hybrid.reranker, candidate_k=4)


@pytest.fixture(scope="module")
def queries():
    return [
        ArenaQuery(query="What is machine learning?", relevant_chunks={"arena_c1"}),
        ArenaQuery(
            query="What does CODE-42 mean?",
            relevant_chunks={"arena_c2"},
            category="identifier",
        ),
        ArenaQuery(
            query="How does redis caching speed up retrieval?",
            relevant_chunks={"arena_c3"},
        ),
    ]


@pytest.fixture(scope="module")
def report(arena, queries):
    return arena.run(queries, k=3, ks=[1, 3])


def test_pipeline_catalog_matches_plan():
    assert PIPELINE_ORDER == (
        "dense", "bm25", "hybrid", "hybrid_rerank", "adaptive", "adaptive_rerank"
    )
    assert PIPELINE_LABELS["hybrid_rerank"] == "Hybrid + Reranker"
    assert PIPELINE_LABELS["adaptive_rerank"] == "Adaptive + Reranker"


def test_arena_runs_every_pipeline_with_full_metrics(report):
    assert report["meta"]["num_queries"] == 3
    assert report["meta"]["corpus_size"] == len(CORPUS)
    assert report["meta"]["primary_metric"] == "ndcg@3"

    names = [row["name"] for row in report["pipelines"]]
    assert sorted(names) == sorted(PIPELINE_ORDER)

    ranks = sorted(row["rank"] for row in report["pipelines"])
    assert ranks == list(range(1, len(PIPELINE_ORDER) + 1))

    for row in report["pipelines"]:
        assert set(row["performance"]) >= {
            "p50_ms", "p95_ms", "p99_ms", "mean_ms", "throughput_qps", "total_queries"
        }
        assert set(row["cost"]) >= {
            "estimated_query_embeddings", "rerank_pairs", "estimated_cost_usd"
        }
        for k in report["meta"]["ks"]:
            assert f"recall@{k}" in row["quality"]
            assert f"ndcg@{k}" in row["quality"]
        assert 0.0 <= row["primary_score"] <= 1.0
        assert row["performance"]["total_queries"] == 3


def test_arena_ranks_are_deterministic_across_runs(arena, queries, report):
    repeat = arena.run(queries, k=3, ks=[1, 3])
    assert [row["name"] for row in repeat["pipelines"]] == [
        row["name"] for row in report["pipelines"]
    ]
    assert [row["rank"] for row in repeat["pipelines"]] == [
        row["rank"] for row in report["pipelines"]
    ]


def test_bm25_pipeline_hits_exact_identifier(report):
    bm25 = next(row for row in report["pipelines"] if row["name"] == "bm25")
    assert bm25["quality"]["recall@3"] == pytest.approx(1.0)
    assert bm25["quality"]["mrr"] == pytest.approx(1.0)
    assert report["per_query"]["bm25"]["What does CODE-42 mean?"]["hit_at_k"] is True


def test_cost_model_and_rerank_pair_accounting(report):
    rows = {row["name"]: row for row in report["pipelines"]}

    # BM25 never embeds or reranks, so it must report zero cost.
    assert rows["bm25"]["cost"]["estimated_query_embeddings"] == 0
    assert rows["bm25"]["cost"]["estimated_cost_usd"] == 0.0

    # Dense pipelines embed exactly once per query.
    assert rows["dense"]["cost"]["estimated_query_embeddings"] == 3

    # Reranking pipelines measure real scorer pairs and pay more than plain hybrid.
    assert 0 < rows["hybrid_rerank"]["cost"]["rerank_pairs"] <= 3 * len(CORPUS)
    assert rows["adaptive_rerank"]["cost"]["rerank_pairs"] > 0
    assert rows["hybrid_rerank"]["cost"]["estimated_cost_usd"] > rows["hybrid"]["cost"]["estimated_cost_usd"]


def test_counting_reranker_counts_pairs_without_mutating_wrapped_model():
    class _StubReranker:
        def __init__(self):
            self.calls = []

        def score(self, query, texts):
            self.calls.append((query, tuple(texts)))
            return [0.5 for _ in texts]

    stub = _StubReranker()
    proxy = CountingReranker(stub)
    assert (proxy.pairs, proxy.calls) == (0, 0)

    scores = proxy.score("q", ["a", "b", "c"])
    assert scores == [0.5, 0.5, 0.5]
    assert (proxy.pairs, proxy.calls) == (3, 1)
    assert stub.calls == [("q", ("a", "b", "c"))]


def test_report_serializes_and_renders_offline(report):
    parsed = json.loads(to_json(report))
    assert parsed["meta"]["num_queries"] == 3
    assert parsed["winners"]["quality"] in PIPELINE_ORDER

    leaderboard = render_leaderboard(report)
    assert "Hybrid + Reranker" in leaderboard
    assert "Winners ->" in leaderboard

    html = render_dashboard(report)
    for label in PIPELINE_LABELS.values():
        assert label in html
    assert "Per-query drilldown" in html
    # The dashboard must render fully offline: no CDN, scripts or remote assets.
    assert "http://" not in html
    assert "https://" not in html
    assert "<script" not in html


def test_self_labeled_queries_are_grounded_in_corpus():
    corpus = {cid: text for cid, text in CORPUS}
    probes = build_self_labeled_queries(corpus, max_queries=3)
    assert len(probes) == 3
    for probe in probes:
        assert probe.category == "self_labeled"
        assert len(probe.relevant_chunks) == 1
        assert next(iter(probe.relevant_chunks)) in corpus
        assert probe.query.strip()

    # Chunks without enough significant terms yield no probe.
    assert build_self_labeled_queries({"tiny": "hi there"}, max_queries=5) == []


def test_arena_queries_from_robustness_suite():
    cases = build_default_robustness_suite("arena_c1", "arena_c2", "arena_c4")
    converted = build_arena_queries_from_test_cases(cases)
    assert len(converted) == len(cases)
    assert converted[0].category == "short"
    assert any("arena_c2" in case.relevant_chunks for case in converted)
    assert any(case.category == "typos" for case in converted)


def test_arena_input_validation(arena, queries):
    with pytest.raises(ValueError):
        arena.run([], k=3)
    with pytest.raises(ValueError):
        arena.run(queries, k=3, pipelines=["not_a_pipeline"])


@pytest.mark.asyncio
async def test_arena_api_endpoints():
    from api.app import app

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            idx_payload = {
                "chunks": [
                    {"chunk_id": cid, "text": text, "metadata": {"source": "arena.txt"}}
                    for cid, text in CORPUS
                ]
            }
            idx_res = await client.post("/api/v1/index", json=idx_payload)
            assert idx_res.status_code == 201

            arena_payload = {
                "queries": [
                    {
                        "query": "What is machine learning?",
                        "relevant_chunk_ids": ["arena_c1"],
                        "category": "concept",
                    },
                    {
                        "query": "What does CODE-42 mean?",
                        "relevant_chunk_ids": ["arena_c2"],
                        "category": "identifier",
                    },
                ],
                "k": 2,
                "ks": [1, 2],
                "candidate_k": 2,
            }

            res = await client.post("/api/v1/arena", json=arena_payload)
            assert res.status_code == 200
            assert "X-Response-Time-Ms" in res.headers

            data = res.json()
            assert data["meta"]["num_queries"] == 2
            assert data["meta"]["ks"] == [1, 2]
            assert sorted(row["name"] for row in data["pipelines"]) == sorted(PIPELINE_ORDER)
            assert len(data["leaderboard"]) == len(PIPELINE_ORDER)
            assert data["winners"]["quality"] in PIPELINE_ORDER
            assert data["per_query"]["bm25"]["What does CODE-42 mean?"]["hit_at_k"] is True

            # Pipeline subset + per-query suppression.
            subset = await client.post(
                "/api/v1/arena",
                json={**arena_payload, "pipelines": ["bm25", "dense"], "include_per_query": False},
            )
            assert subset.status_code == 200
            subset_data = subset.json()
            assert sorted(row["name"] for row in subset_data["pipelines"]) == ["bm25", "dense"]
            assert subset_data["per_query"] is None

            # Unknown pipeline is a client error, not a crash.
            bad = await client.post(
                "/api/v1/arena", json={**arena_payload, "pipelines": ["does_not_exist"]}
            )
            assert bad.status_code == 400

            # Offline HTML dashboard for the live index.
            dash = await client.get("/arena?k=2&limit=3")
            assert dash.status_code == 200
            assert dash.headers["content-type"].startswith("text/html")
            assert "Retrieval Benchmark Arena" in dash.text
            assert "http://" not in dash.text

            metrics = await client.get("/metrics")
            assert b"semanticsearchx_arena_runs_total" in metrics.content
            assert b"semanticsearchx_arena_pipeline_score" in metrics.content

