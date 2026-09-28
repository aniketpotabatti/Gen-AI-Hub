"""Demo script for Phase 9: Productionization.

Demonstrates:
1. Production configuration loading (YAML + environment overrides).
2. FastAPI application startup and lifecycle.
3. Batch document ingestion via `/api/v1/index`.
4. Adaptive hybrid search with full explainability via `/api/v1/search`.
5. Multi-tier caching speedup (comparing cold retrieval vs warm cache hit).
6. Retrieval failure categorization via `/api/v1/diagnose`.
7. Prometheus observability metrics scraping via `/metrics`.
8. System health check via `/health`.
"""
import asyncio
import httpx

from api.app import app
from configs import settings


async def main():
    print("=" * 70)
    print("  SemanticSearchX — Phase 9: Productionization Demo")
    print("=" * 70)

    print("\n[1] Application & Production Configuration:")
    print(f"  • App Name:          {settings.app.name} (v{settings.app.version})")
    print(f"  • Vector Store:      {settings.vector_store.backend} (dim={settings.vector_store.embedding_dim})")
    print(f"  • Cache:             Enabled={settings.cache.enabled} (TTL={settings.cache.ttl_seconds}s)")
    print(f"  • Observability:     Service={settings.observability.service_name}, Metrics={settings.observability.enable_metrics}")

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:

            # 1. Health check
            print("\n[2] Health Check (`/health`):")
            h_res = await client.get("/health")
            h_json = h_res.json()
            print(f"  • Status:            {h_json['status'].upper()}")
            print(f"  • Backend Store:     {h_json['vector_store']}")
            print(f"  • Cache Mode:        {h_json['cache_status']['backend']}")
            print(f"  • Chunks Indexed:    {h_json['indexed_chunks']}")

            # 2. Batch ingestion
            print("\n[3] Ingesting Production Knowledge Base (`/api/v1/index`):")
            corpus = [
                {
                    "chunk_id": "prod_arch_01",
                    "text": "FastAPI powers async high-concurrency microservices with automated OpenAPI docs and strict Pydantic model validation.",
                    "metadata": {"doc_id": "arch_doc", "topic": "web_framework", "environment": "production"},
                },
                {
                    "chunk_id": "prod_cache_02",
                    "text": "Redis multi-tier caching with in-memory LRU fallback ensures sub-millisecond retrieval responses on repeated queries.",
                    "metadata": {"doc_id": "cache_doc", "topic": "caching", "environment": "production"},
                },
                {
                    "chunk_id": "prod_vector_03",
                    "text": "Qdrant and FAISS deliver high-dimensional similarity search with cosine distance and exact payload filtering.",
                    "metadata": {"doc_id": "vector_doc", "topic": "vector_db", "environment": "production"},
                },
                {
                    "chunk_id": "prod_obs_04",
                    "text": "Prometheus metric counters and histograms paired with OpenTelemetry spans provide end-to-end latency and error visibility.",
                    "metadata": {"doc_id": "obs_doc", "topic": "monitoring", "environment": "production"},
                },
            ]
            idx_res = await client.post("/api/v1/index", json={"chunks": corpus})
            idx_data = idx_res.json()
            print(f"  • Index Status:      {idx_data['status']}")
            print(f"  • Ingested Chunks:   {idx_data['indexed_count']}")
            print(f"  • Total in Store:    {idx_data['total_indexed']}")
            print(f"  • Ingest Duration:   {idx_data['duration_ms']:.2f} ms")

            # 3. Search (Cold request)
            print("\n[4] Search Request (Cold — Cache Miss) (`/api/v1/search`):")
            query = "How does Redis multi-tier caching work?"
            req_body = {
                "query": query,
                "k": 2,
                "dense_weight": 0.5,
                "use_reranker": True,
                "explain": True,
                "bypass_cache": False,
            }
            s1_res = await client.post("/api/v1/search", json=req_body)
            s1_data = s1_res.json()
            print(f"  • Query:             {s1_data['query']}")
            print(f"  • Cache Hit:         {s1_data['cache_hit']}")
            print(f"  • Route Decision:    {s1_data['route_decision']['category']} (dense={s1_data['route_decision']['weights']['dense']:.2f}, bm25={s1_data['route_decision']['weights']['bm25']:.2f})")
            print(f"  • Latency:           {s1_data['execution_time_ms']:.2f} ms")
            print(f"  • Top Chunk Retrieved: [{s1_data['results'][0]['chunk_id']}] (Score: {s1_data['results'][0]['score']})")
            print(f"    Text: {s1_data['results'][0]['text'][:85]}...")
            if s1_data['results'][0].get("explanation"):
                exp = s1_data['results'][0]["explanation"]
                print(f"    Explainability: Signals={len(exp.get('signals', []))}, Strategy Breakdown={exp.get('components')}")

            # 4. Search (Warm request — Cache Hit)
            print("\n[5] Search Request (Warm — Cache Hit) (`/api/v1/search`):")
            s2_res = await client.post("/api/v1/search", json=req_body)
            s2_data = s2_res.json()
            print(f"  • Query:             {s2_data['query']}")
            print(f"  • Cache Hit:         {s2_data['cache_hit']}")
            print(f"  • Latency:           {s2_data['execution_time_ms']:.2f} ms")
            speedup = s1_data['execution_time_ms'] / max(s2_data['execution_time_ms'], 0.01)
            print(f"  • Cache Speedup:     {speedup:.1f}x faster")

            # 5. Failure Diagnosis Endpoint
            print("\n[6] Automated Retrieval Diagnosis (`/api/v1/diagnose`):")
            diag_req = {
                "query": "Where is the Quantum Teleportation module?",
                "expected_relevant_ids": ["quantum_teleport_404"],
            }
            d_res = await client.post("/api/v1/diagnose", json=diag_req)
            d_data = d_res.json()
            print(f"  • Diagnosed Category: {d_data['category']}")
            print(f"  • Confidence:         {d_data['confidence']:.2f}")
            print(f"  • Root Cause:         {d_data['reason']}")
            print(f"  • Remediation:        {d_data['recommended_action']}")

            # 6. Observability Metrics
            print("\n[7] Production Observability (`/metrics`):")
            m_res = await client.get("/metrics")
            lines = [line for line in m_res.text.split("\n") if line.startswith("semanticsearchx_") and not line.startswith("#")]
            for line in lines[:6]:
                print(f"  • {line}")

    print("\n" + "=" * 70)
    print("  Phase 9 Demo Completed Successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
