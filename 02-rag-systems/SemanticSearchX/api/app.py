"""FastAPI application for SemanticSearchX."""
from contextlib import asynccontextmanager
import time
from typing import Any, Dict, List, Optional
import os

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from configs import settings
from cache import RetrievalCache
from dense_retrieval import VectorStore, QdrantVectorStore, QDRANT_AVAILABLE
from sparse_retrieval.bm25 import BM25Index
from sparse_retrieval.exact_match import ExactMatchIndex
from embeddings.base import EmbeddingModel
from reranking.cross_encoder import Reranker
from hybrid_retrieval.fusion import HybridRetriever
from adaptive_router.router import AdaptiveRetriever
from evaluation.explainability import RetrievalExplainer
from evaluation.arena import (
    ArenaQuery,
    RetrievalArena,
    build_self_labeled_queries,
    render_dashboard,
)
from failure_analysis import FailureCategorizer
from observability import (
    setup_logging,
    get_latest_metrics,
    CONTENT_TYPE_LATEST,
    SEARCH_REQUEST_TOTAL,
    SEARCH_LATENCY_SECONDS,
    INDEXED_CHUNKS_TOTAL,
    CACHE_OPERATIONS_TOTAL,
    FAILURE_DIAGNOSES_TOTAL,
    ARENA_RUNS_TOTAL,
    ARENA_PIPELINE_SCORE,
)
from api.schemas import (
    SearchRequest,
    SearchResponse,
    RetrievedDocument,
    IndexRequest,
    IndexResponse,
    DiagnoseRequest,
    DiagnoseResponse,
    HealthResponse,
    ArenaRequest,
    ArenaResponse,
)

logger = setup_logging(
    level=settings.observability.log_level,
    structured_json=settings.observability.structured_json,
)


class RetrievalEngineState:
    """Manages retriever lifecycle and state."""

    def __init__(self):
        self.embed_model = EmbeddingModel(dim=settings.vector_store.embedding_dim)
        self.reranker = Reranker()

        # Vector store backend selection
        if settings.vector_store.backend == "qdrant" and QDRANT_AVAILABLE:
            self.vector_store = QdrantVectorStore(
                dimension=settings.vector_store.embedding_dim,
                collection_name=settings.vector_store.collection_name,
                location=settings.vector_store.qdrant_location,
                host=settings.vector_store.qdrant_host,
                port=settings.vector_store.qdrant_port,
            )
            self.backend_name = "qdrant"
        else:
            self.vector_store = VectorStore(dimension=settings.vector_store.embedding_dim)
            self.backend_name = "faiss"

        self.bm25_index = BM25Index()
        self.exact_index = ExactMatchIndex()

        self.hybrid = HybridRetriever(
            vector_store=self.vector_store,
            bm25_index=self.bm25_index,
            exact_index=self.exact_index,
            embed_model=self.embed_model,
            reranker=self.reranker,
        )
        self.adaptive_retriever = AdaptiveRetriever(self.hybrid)
        self.explainer = RetrievalExplainer()
        self.cache = RetrievalCache(
            redis_url=settings.cache.redis_url,
            default_ttl=settings.cache.ttl_seconds,
            max_memory_items=settings.cache.max_memory_items,
            enabled=settings.cache.enabled,
        )

    def get_corpus(self) -> Dict[str, str]:
        corpus = {}
        for text, meta in zip(self.bm25_index.texts, self.bm25_index.metadatas):
            cid = meta.get("chunk_id")
            if cid:
                corpus[cid] = text
        return corpus

    def get_corpus_metas(self) -> Dict[str, Dict[str, Any]]:
        metas = {}
        for meta in self.bm25_index.metadatas:
            cid = meta.get("chunk_id")
            if cid:
                metas[cid] = meta
        return metas

    def get_corpus_texts(self) -> Dict[str, str]:
        """Map chunk_id -> chunk text for arena/self-labeling utilities."""
        return self.get_corpus()

    def run_arena(
        self,
        arena_queries: List[ArenaQuery],
        k: int = 5,
        ks: Optional[List[int]] = None,
        pipelines: Optional[List[str]] = None,
        candidate_k: int = 20,
    ) -> Dict[str, Any]:
        """Execute the retrieval benchmark arena over the live engine."""
        arena = RetrievalArena(
            hybrid=self.hybrid,
            adaptive=self.adaptive_retriever,
            reranker=self.reranker,
            candidate_k=candidate_k,
        )
        return arena.run(arena_queries, k=k, ks=ks, pipelines=pipelines)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global state
    logger.info("Initializing SemanticSearchX engine...")
    state = RetrievalEngineState()
    INDEXED_CHUNKS_TOTAL.set(len(state.vector_store))
    logger.info(
        "SemanticSearchX engine ready (backend=%s, cache=%s)",
        state.backend_name,
        state.cache.stats()["backend"],
    )
    yield
    logger.info("Shutting down SemanticSearchX engine...")


app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    description="Adaptive Semantic Retrieval and Search Intelligence Engine REST API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_timing_and_metrics_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
    return response


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    if not state:
        raise HTTPException(status_code=503, detail="Retrieval engine uninitialized")

    indexed_count = len(state.vector_store)
    INDEXED_CHUNKS_TOTAL.set(indexed_count)

    return HealthResponse(
        status="healthy",
        app=settings.app.name,
        version=settings.app.version,
        vector_store=state.backend_name,
        indexed_chunks=indexed_count,
        cache_status=state.cache.stats(),
    )


@app.get("/metrics", tags=["System"])
def metrics():
    return Response(content=get_latest_metrics(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/search", response_model=SearchResponse, tags=["Retrieval"])
def search(request: SearchRequest):
    if not state:
        raise HTTPException(status_code=503, detail="Retrieval engine uninitialized")

    start_time = time.perf_counter()
    cache_key = state.cache.generate_key("search", request.model_dump())

    # Check cache
    if not request.bypass_cache:
        cached = state.cache.get(cache_key)
        if cached:
            CACHE_OPERATIONS_TOTAL.labels(operation="get", result="hit").inc()
            duration_ms = (time.perf_counter() - start_time) * 1000
            SEARCH_REQUEST_TOTAL.labels(status="success", strategy="cached", cache_hit="true").inc()
            cached["execution_time_ms"] = round(duration_ms, 2)
            cached["cache_hit"] = True
            return SearchResponse(**cached)
        CACHE_OPERATIONS_TOTAL.labels(operation="get", result="miss").inc()

    # Execute adaptive retrieval
    try:
        search_res = state.adaptive_retriever.search(
            query=request.query,
            k=request.k,
            metadata_filter=request.metadata_filter,
            explain=request.explain,
        )
    except Exception as e:
        SEARCH_REQUEST_TOTAL.labels(status="error", strategy="unknown", cache_hit="false").inc()
        logger.error("Retrieval error for query %r: %s", request.query, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    raw_results = search_res.get("results", [])
    route = search_res.get("route", {})
    route_strat = route.get("category", "hybrid")

    doc_results: List[RetrievedDocument] = []
    for r in raw_results:
        cid = r.get("chunk_id", "")
        meta = r.get("metadata", {})
        text = state.hybrid._full_text(cid, meta) or meta.get("content", "")
        score = float(r.get("reranker_norm", r.get("rrf_score", 0.0)))
        doc_results.append(
            RetrievedDocument(
                chunk_id=cid,
                text=text,
                score=round(score, 4),
                metadata=meta,
                explanation=r.get("explanation"),
            )
        )

    duration_sec = time.perf_counter() - start_time
    duration_ms = duration_sec * 1000

    SEARCH_LATENCY_SECONDS.labels(strategy=route_strat).observe(duration_sec)
    SEARCH_REQUEST_TOTAL.labels(status="success", strategy=route_strat, cache_hit="false").inc()

    response_data = {
        "query": request.query,
        "results": [d.model_dump() for d in doc_results],
        "total_retrieved": len(doc_results),
        "execution_time_ms": round(duration_ms, 2),
        "cache_hit": False,
        "route_decision": route,
    }

    # Store into cache
    if not request.bypass_cache:
        state.cache.set(cache_key, response_data)
        CACHE_OPERATIONS_TOTAL.labels(operation="set", result="success").inc()

    return SearchResponse(**response_data)


@app.post("/api/v1/index", response_model=IndexResponse, status_code=status.HTTP_201_CREATED, tags=["Ingestion"])
def index_documents(request: IndexRequest):
    if not state:
        raise HTTPException(status_code=503, detail="Retrieval engine uninitialized")

    start_time = time.perf_counter()
    chunks = [c.text for c in request.chunks]
    metadatas = [
        {"chunk_id": c.chunk_id, **(c.metadata or {})}
        for c in request.chunks
    ]

    try:
        embeddings = state.embed_model.encode(chunks)
        indexed = state.hybrid.index_chunks(chunks, metadatas, embeddings)
    except Exception as e:
        logger.error("Indexing failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    total = len(state.vector_store)
    INDEXED_CHUNKS_TOTAL.set(total)
    duration_ms = (time.perf_counter() - start_time) * 1000

    return IndexResponse(
        status="success",
        indexed_count=indexed,
        total_indexed=total,
        duration_ms=round(duration_ms, 2),
    )


@app.post("/api/v1/diagnose", response_model=DiagnoseResponse, tags=["Failure Analysis"])
def diagnose_retrieval(request: DiagnoseRequest):
    if not state:
        raise HTTPException(status_code=503, detail="Retrieval engine uninitialized")

    corpus = state.get_corpus()
    corpus_metas = state.get_corpus_metas()
    categorizer = FailureCategorizer(corpus, corpus_metas)

    diagnosis = categorizer.diagnose(
        query=request.query,
        retrieved_results=request.retrieved_results,
        expected_relevant_ids=set(request.expected_relevant_ids),
        candidate_pool=request.candidate_pool,
        applied_metadata_filter=request.applied_metadata_filter,
        route_decision=request.route_decision,
        sub_query_results=request.sub_query_results,
        is_known_out_of_corpus=request.is_known_out_of_corpus,
    )

    FAILURE_DIAGNOSES_TOTAL.labels(category=diagnosis.category.value).inc()

    return DiagnoseResponse(
        query=diagnosis.query,
        category=diagnosis.category.value,
        confidence=diagnosis.confidence,
        reason=diagnosis.reason,
        recommended_action=diagnosis.recommended_action,
        diagnostics=diagnosis.diagnostics,
    )



def _record_arena_metrics(report: Dict[str, Any]) -> None:
    """Publish the latest arena outcome to Prometheus gauges."""
    primary = report["meta"]["primary_metric"]
    for row in report["pipelines"]:
        ARENA_PIPELINE_SCORE.labels(pipeline=row["name"], metric=primary).set(row["primary_score"])
        ARENA_PIPELINE_SCORE.labels(pipeline=row["name"], metric="mrr").set(
            row["quality"].get("mrr", 0.0))
        ARENA_PIPELINE_SCORE.labels(pipeline=row["name"], metric="mean_ms").set(
            row["performance"]["mean_ms"])
        ARENA_PIPELINE_SCORE.labels(pipeline=row["name"], metric="cost_usd").set(
            row["cost"]["estimated_cost_usd"])


@app.post("/api/v1/arena", response_model=ArenaResponse, tags=["Benchmark"])
def run_benchmark_arena(request: ArenaRequest):
    """Run the head-to-head retrieval pipeline benchmark (Dense/BM25/Hybrid/Adaptive)."""
    if not state:
        raise HTTPException(status_code=503, detail="Retrieval engine uninitialized")

    if not state.get_corpus():
        raise HTTPException(
            status_code=409,
            detail="Corpus is empty; index chunks via /api/v1/index before benchmarking",
        )

    arena_queries = [
        ArenaQuery(
            query=q.query,
            relevant_chunks=set(q.relevant_chunk_ids),
            category=q.category,
            metadata_filter=q.metadata_filter,
        )
        for q in request.queries
    ]

    try:
        report = state.run_arena(
            arena_queries,
            k=request.k,
            ks=request.ks,
            pipelines=request.pipelines,
            candidate_k=request.candidate_k,
        )
    except ValueError as e:
        ARENA_RUNS_TOTAL.labels(status="invalid").inc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        ARENA_RUNS_TOTAL.labels(status="error").inc()
        logger.error("Benchmark arena failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    ARENA_RUNS_TOTAL.labels(status="success").inc()
    _record_arena_metrics(report)
    logger.info(
        "Arena run complete (queries=%d, corpus=%d, winner=%s)",
        report["meta"]["num_queries"],
        report["meta"]["corpus_size"],
        report["winners"]["quality"],
    )

    if not request.include_per_query:
        report = {**report, "per_query": None}

    return ArenaResponse(**report)


@app.get("/arena", response_class=HTMLResponse, tags=["Benchmark"])
def benchmark_dashboard(k: int = 5, limit: int = 10, candidate_k: int = 20):
    """Render the offline benchmark arena dashboard for the live index."""
    if not state:
        raise HTTPException(status_code=503, detail="Retrieval engine uninitialized")

    corpus_texts = state.get_corpus_texts()
    if not corpus_texts:
        return HTMLResponse(
            content=(
                "<html><body style='background:#0f1420;color:#e8edf7;"
                "font-family:Segoe UI,sans-serif;padding:32px'>"
                "<h1>Retrieval Benchmark Arena</h1>"
                "<p>The corpus is empty. Ingest chunks via "
                "<code>POST /api/v1/index</code>, then reload this dashboard.</p>"
                "</body></html>"
            ),
            status_code=409,
        )

    limit = max(1, min(limit, 50))
    arena_queries = build_self_labeled_queries(corpus_texts, max_queries=limit)
    if not arena_queries:
        raise HTTPException(
            status_code=409,
            detail="Corpus chunks are too short to derive self-labeled probe queries",
        )

    try:
        report = state.run_arena(
            arena_queries, k=max(1, min(k, 50)), candidate_k=candidate_k)
    except Exception as e:
        ARENA_RUNS_TOTAL.labels(status="error").inc()
        logger.error("Benchmark dashboard failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    ARENA_RUNS_TOTAL.labels(status="success").inc()
    _record_arena_metrics(report)
    return HTMLResponse(content=render_dashboard(report))





state: Optional[RetrievalEngineState] = None
