"""HTTP client for the SemanticSearchX FastAPI backend.

The dashboard is a separate process from the API and communicates purely over
HTTP, so it never imports the retrieval core (Torch / FAISS / Qdrant / Redis).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import httpx

from dashboard.config import api_base_url, request_timeout


class ApiError(RuntimeError):
    """Raised when the backend is unreachable or returns a non-2xx status."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _extract_detail(response: httpx.Response) -> str:
    """Best-effort extraction of FastAPI's ``{"detail": ...}`` error body."""
    try:
        body = response.json()
    except ValueError:
        text = response.text.strip()
        return f"HTTP {response.status_code}: {text[:300] or response.reason_phrase}"
    if isinstance(body, dict) and "detail" in body:
        return f"HTTP {response.status_code}: {body['detail']}"
    return f"HTTP {response.status_code}: {body}"


class SemanticSearchClient:
    """Minimal, dependency-light wrapper around the REST endpoints."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.base_url = (base_url or api_base_url()).rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout if timeout is not None else request_timeout(),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SemanticSearchClient":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:  # network / DNS / timeout
            raise ApiError(f"Could not reach the API at {self.base_url}: {exc}") from exc
        if response.status_code >= 400:
            raise ApiError(_extract_detail(response), status_code=response.status_code)
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return response.text

    def health(self) -> Dict[str, Any]:
        """GET /health - liveness plus index and cache stats."""
        return self._request("GET", "/health")

    def metrics_text(self) -> str:
        """GET /metrics - Prometheus exposition text."""
        return self._request("GET", "/metrics")

    # -- retrieval ---------------------------------------------------------
    def search(
        self,
        query: str,
        *,
        k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        dense_weight: float = 0.5,
        use_reranker: bool = True,
        explain: bool = False,
        bypass_cache: bool = False,
    ) -> Dict[str, Any]:
        """POST /api/v1/search."""
        payload: Dict[str, Any] = {
            "query": query,
            "k": k,
            "metadata_filter": metadata_filter,
            "dense_weight": dense_weight,
            "use_reranker": use_reranker,
            "explain": explain,
            "bypass_cache": bypass_cache,
        }
        return self._request("POST", "/api/v1/search", json=payload)

    # -- ingestion ---------------------------------------------------------
    def index_chunks(self, chunks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        """POST /api/v1/index with ``[{chunk_id, text, metadata}, ...]``."""
        return self._request("POST", "/api/v1/index", json={"chunks": list(chunks)})

    def corpus(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        q: Optional[str] = None,
    ) -> Dict[str, Any]:
        """GET /api/v1/corpus - paginated listing of indexed chunks."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if q:
            params["q"] = q
        return self._request("GET", "/api/v1/corpus", params=params)

    # -- analysis ----------------------------------------------------------
    def diagnose(
        self,
        query: str,
        *,
        retrieved_results: Optional[List[Dict[str, Any]]] = None,
        expected_relevant_ids: Optional[List[str]] = None,
        applied_metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST /api/v1/diagnose - failure categorization for one query."""
        payload = {
            "query": query,
            "retrieved_results": retrieved_results or [],
            "expected_relevant_ids": expected_relevant_ids or [],
            "applied_metadata_filter": applied_metadata_filter,
        }
        return self._request("POST", "/api/v1/diagnose", json=payload)

    # -- benchmark ---------------------------------------------------------
    def run_arena(
        self,
        queries: Iterable[Dict[str, Any]],
        *,
        k: int = 5,
        ks: Optional[List[int]] = None,
        pipelines: Optional[List[str]] = None,
        candidate_k: int = 20,
        include_per_query: bool = True,
    ) -> Dict[str, Any]:
        """POST /api/v1/arena - head-to-head pipeline benchmark."""
        payload: Dict[str, Any] = {
            "queries": list(queries),
            "k": k,
            "ks": ks or [1, 3, 5],
            "pipelines": pipelines,
            "candidate_k": candidate_k,
            "include_per_query": include_per_query,
        }
        return self._request("POST", "/api/v1/arena", json=payload)

    def arena_html(self, *, k: int = 5, limit: int = 10, candidate_k: int = 20) -> str:
        """GET /arena - the offline, self-contained HTML benchmark report."""
        return self._request(
            "GET",
            "/arena",
            params={"k": k, "limit": limit, "candidate_k": candidate_k},
        )
