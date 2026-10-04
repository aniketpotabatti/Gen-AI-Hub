"""Shared Streamlit runtime helpers (cached resources and catalog constants)."""
from __future__ import annotations

import streamlit as st

from dashboard.api_client import SemanticSearchClient
from dashboard.config import api_base_url, request_timeout

# Pipeline identifiers and labels mirror ``evaluation.arena.PIPELINE_LABELS`` so
# the UI can offer a pipeline selector without importing the heavy evaluation
# package (which pulls in the retrieval core).
PIPELINE_LABELS: dict[str, str] = {
    "dense": "Dense",
    "bm25": "BM25",
    "hybrid": "Hybrid",
    "hybrid_rerank": "Hybrid + Reranker",
    "adaptive": "Adaptive",
    "adaptive_rerank": "Adaptive + Reranker",
}


@st.cache_resource(show_spinner=False)
def _cached_client(base_url: str, timeout: float) -> SemanticSearchClient:
    """Create one HTTP client per (base_url, timeout) for the whole process."""
    return SemanticSearchClient(base_url=base_url, timeout=timeout)


def api_client() -> SemanticSearchClient:
    """Return the process-wide, cached client for the backend."""
    return _cached_client(api_base_url(), request_timeout())
