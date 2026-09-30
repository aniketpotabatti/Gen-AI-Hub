"""Unit and integration tests for Phase 9: Productionization."""
import pytest
import numpy as np
import httpx
from configs import Settings
from cache import RetrievalCache, InMemoryLRUCache
from dense_retrieval.qdrant_store import QdrantVectorStore, QDRANT_AVAILABLE
from api.app import app


def test_settings_load():
    cfg = Settings()
    assert cfg.app.name == "SemanticSearchX"
    assert cfg.vector_store.backend in ("faiss", "qdrant")
    assert cfg.cache.enabled is True
    assert cfg.observability.service_name == "semantic-search-x"


def test_in_memory_lru_cache():
    cache = InMemoryLRUCache(maxsize=2, default_ttl=60)
    cache.set("a", 10)
    cache.set("b", 20)
    assert cache.get("a") == 10
    assert cache.get("b") == 20

    # Test eviction: inserting 'c' should evict 'a' (oldest access was 'a')
    cache.set("c", 30)
    assert cache.get("c") == 30
    assert len(cache) == 2


def test_retrieval_cache():
    retrieval_cache = RetrievalCache(redis_url=None, default_ttl=3600)
    key = retrieval_cache.generate_key("query", {"query": "test query", "k": 5})
    payload = {"results": [{"chunk_id": "c1", "score": 0.99}]}

    assert retrieval_cache.get(key) is None
    retrieval_cache.set(key, payload)
    cached = retrieval_cache.get(key)

    assert cached is not None
    assert cached["results"][0]["chunk_id"] == "c1"
    stats = retrieval_cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="qdrant-client not installed")
def test_qdrant_vector_store():
    store = QdrantVectorStore(dimension=4, location=":memory:")
    vecs = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=np.float32)
    metas = [{"chunk_id": "c1", "type": "code"}, {"chunk_id": "c2", "type": "doc"}]

    ids = store.add_vectors(vecs, metas)
    assert len(ids) == 2
    assert len(store) == 2

    q = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    ret_ids, scores, ret_metas = store.search(q, k=1)
    assert len(ret_ids) == 1
    assert ret_metas[0]["chunk_id"] == "c1"

    # Filtered search
    _, _, f_metas = store.search(q, k=2, metadata_filter={"type": "doc"})
    assert len(f_metas) == 1
    assert f_metas[0]["chunk_id"] == "c2"

    # Delete
    deleted = store.delete_by_filter({"type": "code"})
    assert deleted == 1


@pytest.mark.asyncio
async def test_fastapi_endpoints():
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Health check
            h_res = await client.get("/health")
            assert h_res.status_code == 200
            h_data = h_res.json()
            assert h_data["status"] == "healthy"
            assert h_data["app"] == "SemanticSearchX"

            # 2. Ingest / Index
            idx_payload = {
                "chunks": [
                    {
                        "chunk_id": "chunk_api_p9_1",
                        "text": "Vector database caching and adaptive routing make search production-grade.",
                        "metadata": {"source": "phase9_doc", "category": "engineering"},
                    },
                    {
                        "chunk_id": "chunk_api_p9_2",
                        "text": "FastAPI enables rapid schema validation and async API development.",
                        "metadata": {"source": "phase9_doc", "category": "api"},
                    },
                ]
            }
            idx_res = await client.post("/api/v1/index", json=idx_payload)
            assert idx_res.status_code == 201
            assert idx_res.json()["status"] == "success"
            assert idx_res.json()["indexed_count"] >= 1

            # 3. Search
            s_payload = {"query": "vector database caching search", "k": 2, "explain": True}
            s_res = await client.post("/api/v1/search", json=s_payload)
            assert s_res.status_code == 200
            s_data = s_res.json()
            assert s_data["total_retrieved"] >= 1
            assert s_data["cache_hit"] is False
            assert "results" in s_data
            assert "explanation" in s_data["results"][0]

            # 4. Search again -> Cache hit
            s_res2 = await client.post("/api/v1/search", json=s_payload)
            assert s_res2.status_code == 200
            assert s_res2.json()["cache_hit"] is True

            # 5. Failure Diagnosis
            diag_payload = {
                "query": "Where is confidential nuclear launch key?",
                "expected_relevant_ids": ["c_missing_classified_99"],
            }
            d_res = await client.post("/api/v1/diagnose", json=diag_payload)
            assert d_res.status_code == 200
            assert d_res.json()["category"] == "missing_document"

            # 6. Prometheus Metrics
            m_res = await client.get("/metrics")
            assert m_res.status_code == 200
            assert b"semanticsearchx_search_requests_total" in m_res.content
