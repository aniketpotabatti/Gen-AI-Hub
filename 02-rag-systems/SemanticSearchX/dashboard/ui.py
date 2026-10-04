"""Reusable UI helpers, formatting and input parsing for the dashboard."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

import streamlit as st

from dashboard.api_client import ApiError, SemanticSearchClient
from dashboard.parsing import parse_json_object, split_ids

__all__ = [
    "CATEGORY_STYLES",
    "render_page_header",
    "health_or_error",
    "render_sidebar_status",
    "parse_json_object",
    "split_ids",
    "pretty_json",
]

# Category -> (icon, streamlit alert kind) used by the failure-analysis page.
CATEGORY_STYLES: Dict[str, Tuple[str, str]] = {
    "success": (":material/check_circle:", "success"),
    "missing_relevant": (":material/search_off:", "error"),
    "ranking_failure": (":material/swap_vert:", "warning"),
    "metadata_filter_over_restriction": (":material/filter_alt_off:", "warning"),
    "query_ambiguity": (":material/help:", "info"),
    "route_misselection": (":material/wrong_location:", "warning"),
    "out_of_corpus": (":material/public_off:", "info"),
}


def render_page_header(title: str, subtitle: str = "") -> None:
    """Render a compact page header with an optional caption."""
    st.markdown(f"#### {title}")
    if subtitle:
        st.caption(subtitle)


def health_or_error(client: SemanticSearchClient) -> Optional[Dict[str, Any]]:
    """Fetch ``/health``; render a friendly banner and return ``None`` on failure."""
    try:
        return client.health()
    except ApiError as exc:
        st.error(
            f"Backend unreachable at `{client.base_url}`.\n\n{exc}\n\n"
            "Start it with: `uvicorn api.app:app --port 8000`"
        )
        return None


def render_sidebar_status(client: SemanticSearchClient) -> None:
    """Show backend connectivity in the sidebar (shared across all pages)."""
    with st.sidebar:
        st.divider()
        st.caption("Backend")
        try:
            health = client.health()
        except ApiError:
            st.error("offline", icon=":material/cloud_off:")
            st.caption(client.base_url)
            return
        cache = health.get("cache_status", {}) or {}
        st.success(
            f"{str(health.get('vector_store', '?')).upper()} · "
            f"{health.get('indexed_chunks', 0):,} chunks",
            icon=":material/database:",
        )
        st.caption(
            f"cache: {cache.get('backend', 'unknown')} · "
            f"hit rate {cache.get('hit_rate', 0.0):.0%}"
        )
        st.caption(f"api: {client.base_url}")


def pretty_json(data: Any) -> str:
    """Render data as indented JSON for display in code blocks."""
    return json.dumps(data, indent=2, default=str)
