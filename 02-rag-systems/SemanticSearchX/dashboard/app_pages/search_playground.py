"""Search Playground: query the adaptive retriever and inspect each result."""
from __future__ import annotations

import streamlit as st

from dashboard.api_client import ApiError
from dashboard.runtime import api_client
from dashboard.ui import (
    health_or_error,
    parse_json_object,
    pretty_json,
    render_page_header,
)

render_page_header(
    "Search Playground",
    "Run a query through the adaptive hybrid retriever and drill into the results.",
)

client = api_client()
if health_or_error(client) is None:
    st.stop()

with st.form("search_form", border=True):
    query = st.text_input(
        "Query",
        placeholder="e.g. How does the adaptive router choose a pipeline?",
    )
    col_k, col_weight, col_opts = st.columns(3)
    k = col_k.slider("Results (k)", min_value=1, max_value=50, value=5)
    dense_weight = col_weight.slider(
        "Dense weight",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.05,
        help="Blend between dense (1.0) and sparse (0.0) retrieval.",
    )
    col_opts.markdown("**Options**")
    use_reranker = col_opts.toggle("Cross-encoder rerank", value=True)
    explain = col_opts.toggle("Explain results", value=True)
    bypass_cache = col_opts.toggle("Bypass cache", value=False)

    metadata_filter_raw = st.text_input(
        "Metadata filter (JSON, optional)",
        placeholder='{"source": "handbook"}',
    )
    submitted = st.form_submit_button("Search", type="primary", icon=":material/search:")

if submitted:
    if not query.strip():
        st.warning("Enter a query first.")
    else:
        metadata_filter, error = parse_json_object(
            metadata_filter_raw, field="Metadata filter"
        )
        if error:
            st.error(error)
        else:
            with st.spinner("Retrieving..."):
                try:
                    st.session_state["search_response"] = client.search(
                        query=query.strip(),
                        k=k,
                        metadata_filter=metadata_filter,
                        dense_weight=dense_weight,
                        use_reranker=use_reranker,
                        explain=explain,
                        bypass_cache=bypass_cache,
                    )
                except ApiError as exc:
                    st.session_state.pop("search_response", None)
                    st.error(str(exc))

response = st.session_state.get("search_response")
if not response:
    st.stop()

results = response.get("results", [])

with st.container(horizontal=True):
    st.metric("Results", response.get("total_retrieved", len(results)), border=True)
    st.metric("Latency", f"{response.get('execution_time_ms', 0.0):.1f} ms", border=True)
    st.metric("Cache", "hit" if response.get("cache_hit") else "miss", border=True)

route = response.get("route_decision")
if route:
    with st.expander("Routing decision", icon=":material/alt_route:"):
        st.json(route)

best = max((doc.get("score", 0.0) for doc in results), default=1.0) or 1.0

for rank, doc in enumerate(results, start=1):
    score = doc.get("score", 0.0)
    with st.container(border=True):
        head = st.container(horizontal=True, horizontal_alignment="distribute")
        head.markdown(f"**#{rank}** &nbsp; `{doc.get('chunk_id', '?')}`")
        head.markdown(f"score **{score:.4f}**")
        st.progress(min(1.0, max(0.0, score / best)), text=f"relative {score / best:.0%}")
        st.write(doc.get("text", ""))

        metadata = doc.get("metadata") or {}
        if metadata:
            with st.expander("Metadata"):
                st.code(pretty_json(metadata), language="json")

        explanation = doc.get("explanation")
        if explanation:
            with st.expander("Why this result?", icon=":material/lightbulb:"):
                st.json(explanation)

st.caption(
    "Progress bars are relative to the top score of this run; absolute score "
    "scales differ between pipelines."
)
