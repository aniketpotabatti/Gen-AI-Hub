"""Overview: live engine snapshot and the benchmark pipeline catalog."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.runtime import PIPELINE_LABELS, api_client
from dashboard.ui import health_or_error, render_page_header

render_page_header(
    "Overview",
    "Live snapshot of the retrieval engine, its index and the benchmark ladder.",
)

client = api_client()
health = health_or_error(client)
if health is None:
    st.stop()

cache = health.get("cache_status", {}) or {}

with st.container(horizontal=True):
    st.metric("Status", str(health.get("status", "unknown")).title(), border=True)
    st.metric("Indexed chunks", f"{health.get('indexed_chunks', 0):,}", border=True)
    st.metric("Vector store", str(health.get("vector_store", "?")).upper(), border=True)
    st.metric("Cache hit rate", f"{cache.get('hit_rate', 0.0):.0%}", border=True)

left, right = st.columns([3, 2])

with left:
    with st.container(border=True):
        st.markdown("**Benchmark ladder**")
        st.caption("Six pipelines compared head-to-head in the Benchmark Arena.")
        st.dataframe(
            pd.DataFrame(
                {
                    "Pipeline": list(PIPELINE_LABELS.values()),
                    "Id": list(PIPELINE_LABELS.keys()),
                }
            ),
            hide_index=True,
        )

with right:
    with st.container(border=True):
        st.markdown("**Runtime**")
        st.json(
            {
                "app": health.get("app"),
                "version": health.get("version"),
                "cache": cache,
            }
        )

st.info(
    "Start in **Search Playground** to explore retrieval, then **Benchmark Arena** "
    "to compare pipelines on your own labeled queries.",
    icon=":material/tips_and_updates:",
)
