"""Pydantic schemas for the SemanticSearchX REST API."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Query string to search")
    k: int = Field(5, ge=1, le=50, description="Number of results to retrieve")
    metadata_filter: Optional[Dict[str, Any]] = Field(None, description="Metadata filters to apply")
    dense_weight: float = Field(0.5, ge=0.0, le=1.0, description="Dense retrieval weight")
    use_reranker: bool = Field(True, description="Whether to rerank top candidates")
    explain: bool = Field(False, description="Whether to attach detailed retrieval explanation")
    bypass_cache: bool = Field(False, description="Bypass retrieval cache")


class RetrievedDocument(BaseModel):
    chunk_id: str
    text: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    explanation: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    query: str
    results: List[RetrievedDocument]
    total_retrieved: int
    execution_time_ms: float
    cache_hit: bool
    route_decision: Optional[Dict[str, Any]] = None


class DocumentChunkInput(BaseModel):
    chunk_id: str
    text: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class IndexRequest(BaseModel):
    chunks: List[DocumentChunkInput] = Field(..., min_length=1, description="List of chunks to ingest and index")


class IndexResponse(BaseModel):
    status: str
    indexed_count: int
    total_indexed: int
    duration_ms: float


class DiagnoseRequest(BaseModel):
    query: str
    retrieved_results: List[Dict[str, Any]] = Field(default_factory=list)
    expected_relevant_ids: List[str] = Field(default_factory=list)
    candidate_pool: Optional[List[Dict[str, Any]]] = None
    applied_metadata_filter: Optional[Dict[str, Any]] = None
    route_decision: Optional[Dict[str, Any]] = None
    sub_query_results: Optional[Dict[str, List[Any]]] = None
    is_known_out_of_corpus: bool = False


class DiagnoseResponse(BaseModel):
    query: str
    category: str
    confidence: float
    reason: str
    recommended_action: str
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    vector_store: str
    indexed_chunks: int
    cache_status: Dict[str, Any]


class ArenaQueryInput(BaseModel):
    """A single labeled evaluation probe for the benchmark arena."""

    query: str = Field(..., min_length=1, description="Evaluation query text")
    relevant_chunk_ids: List[str] = Field(
        default_factory=list, description="Ground-truth relevant chunk ids"
    )
    category: str = Field("general", description="Optional query category label")
    metadata_filter: Optional[Dict[str, Any]] = Field(
        None, description="Metadata filter applied for this probe"
    )


class ArenaRequest(BaseModel):
    """Configuration for a head-to-head pipeline benchmark run."""

    queries: List[ArenaQueryInput] = Field(..., min_length=1, description="Labeled evaluation queries")
    k: int = Field(5, ge=1, le=50, description="Cutoff used for ranking metrics")
    ks: List[int] = Field(default_factory=lambda: [1, 3, 5], description="All metric cutoffs to report")
    pipelines: Optional[List[str]] = Field(
        None, description="Subset of pipelines to run (default: all six)"
    )
    candidate_k: int = Field(20, ge=1, le=100, description="Candidate depth for reranking pipelines")
    include_per_query: bool = Field(True, description="Include per-query ranked ids in the response")


class ArenaResponse(BaseModel):
    meta: Dict[str, Any]
    pipelines: List[Dict[str, Any]]
    leaderboard: List[Dict[str, Any]]
    winners: Dict[str, Any]
    queries: List[Dict[str, Any]]
    per_query: Optional[Dict[str, Any]] = None
