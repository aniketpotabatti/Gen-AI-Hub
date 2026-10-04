"""Benchmark Arena: run the pipeline ladder and explore the leaderboard."""
from __future__ import annotations

import json
from typing import Any, Dict, List

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from dashboard.api_client import ApiError
from dashboard.runtime import PIPELINE_LABELS, api_client
from dashboard.ui import health_or_error, render_page_header, split_ids

SEED_QUERIES = pd.DataFrame(
    {
        "query": ["", ""],
        "relevant_chunk_ids": ["", ""],
        "category": ["general", "general"],
    }
)


def _queries_from_editor(edited: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert the data-editor frame into the arena query payload."""
    queries: List[Dict[str, Any]] = []
    for row in edited.itertuples():
        text = str(getattr(row, "query", "") or "").strip()
        if not text:
            continue
        queries.append(
            {
                "query": text,
                "relevant_chunk_ids": split_ids(str(getattr(row, "relevant_chunk_ids", "") or "")),
                "category": str(getattr(row, "category", "") or "general").strip() or "general",
            }
        )
    return queries


def _leaderboard_frame(report: Dict[str, Any]) -> pd.DataFrame:
    """Flatten the leaderboard plus per-pipeline perf/cost into one frame."""
    rows = []
    for row in report.get("leaderboard", []):
        full = next(p for p in report["pipelines"] if p["name"] == row["pipeline"])
        rows.append(
            {
                "rank": row["rank"],
                "pipeline": row["label"],
                "primary": row["score"],
                "mrr": row["mrr"],
                "mean_ms": row["mean_ms"],
                "qps": full["performance"].get("throughput_qps", 0.0),
                "cost_usd": row["estimated_cost_usd"],
            }
        )
    return pd.DataFrame(rows)


def _bar_chart(frame: pd.DataFrame, primary: str) -> alt.Chart:
    """Primary metric per pipeline, sorted best-first."""
    return (
        alt.Chart(frame)
        .mark_bar()
        .encode(
            x=alt.X("pipeline:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-20)),
            y=alt.Y("primary:Q", title=primary),
            color=alt.Color("pipeline:N", legend=None),
            tooltip=["pipeline", alt.Tooltip("primary:Q", format=".3f")],
        )
        .properties(height=300)
    )


def _scatter_chart(frame: pd.DataFrame, primary: str) -> alt.Chart:
    """Quality/latency trade-off per pipeline."""
    return (
        alt.Chart(frame)
        .mark_circle(size=150, opacity=0.85)
        .encode(
            x=alt.X("mean_ms:Q", title="Mean latency (ms)"),
            y=alt.Y("primary:Q", title=primary),
            color=alt.Color("pipeline:N", legend=None),
            tooltip=[
                "pipeline",
                alt.Tooltip("mean_ms:Q", format=".1f"),
                alt.Tooltip("primary:Q", format=".3f"),
            ],
        )
        .properties(height=300)
    )


def _drill_frame(details: Dict[str, Any]) -> pd.DataFrame:
    """Per-query hit/miss table for one pipeline."""
    rows = [
        {
            "hit": "yes" if detail.get("hit_at_k") else "no",
            "category": detail.get("category", ""),
            "query": query,
            "ranked": ", ".join(detail.get("ranked", [])),
            "relevant": ", ".join(detail.get("relevant", [])),
        }
        for query, detail in details.items()
    ]
    return pd.DataFrame(rows)


def _render_report(report: Dict[str, Any]) -> None:
    """Render winners, leaderboard, charts, drilldown and downloads."""
    meta = report.get("meta", {})
    primary = meta.get("primary_metric", "score")
    winners = report.get("winners", {}) or {}

    def label_of(name: Any) -> str:
        return PIPELINE_LABELS.get(name, "\u2014") if name else "\u2014"

    st.divider()
    with st.container(horizontal=True):
        st.metric(f"Best quality ({primary})", label_of(winners.get("quality")), border=True)
        st.metric("Fastest (mean)", label_of(winners.get("latency")), border=True)
        st.metric("Highest throughput", label_of(winners.get("throughput")), border=True)
        st.metric("Cheapest", label_of(winners.get("cost")), border=True)

    frame = _leaderboard_frame(report)
    if frame.empty:
        st.info("No pipelines were run.")
        return

    with st.container(border=True):
        st.markdown("**Leaderboard**")
        st.dataframe(
            frame,
            hide_index=True,
            column_config={
                "rank": st.column_config.NumberColumn("#", width="small"),
                "pipeline": st.column_config.TextColumn("Pipeline", pinned=True),
                "primary": st.column_config.ProgressColumn(
                    primary,
                    min_value=0.0,
                    max_value=float(frame["primary"].max()) or 1.0,
                    format="%.3f",
                ),
                "mrr": st.column_config.NumberColumn("MRR", format="%.3f"),
                "mean_ms": st.column_config.NumberColumn("Mean ms", format="%.2f"),
                "qps": st.column_config.NumberColumn("QPS", format="%.1f"),
                "cost_usd": st.column_config.NumberColumn("Est. cost $", format="$%.4f"),
            },
        )

    col_bar, col_scatter = st.columns(2)
    with col_bar:
        with st.container(border=True):
            st.markdown(f"**{primary} by pipeline**")
            st.altair_chart(_bar_chart(frame, primary))
    with col_scatter:
        with st.container(border=True):
            st.markdown("**Quality vs latency**")
            st.altair_chart(_scatter_chart(frame, primary))

    drill = report.get("per_query") or {}
    if drill:
        with st.container(border=True):
            st.markdown("**Per-query drilldown**")
            pipeline = st.selectbox(
                "Pipeline",
                list(drill.keys()),
                format_func=lambda name: PIPELINE_LABELS.get(name, name),
            )
            st.dataframe(_drill_frame(drill.get(pipeline, {})), hide_index=True, height=320)

    col_json, col_csv = st.columns(2)
    col_json.download_button(
        "Download report (JSON)",
        data=json.dumps(report, indent=2, default=str),
        file_name="arena_report.json",
        mime="application/json",
        icon=":material/download:",
    )
    col_csv.download_button(
        "Download leaderboard (CSV)",
        data=frame.to_csv(index=False),
        file_name="arena_leaderboard.csv",
        mime="text/csv",
        icon=":material/download:",
    )


render_page_header(
    "Benchmark Arena",
    "Run the retrieval pipeline ladder head-to-head and explore the leaderboard.",
)

client = api_client()
if health_or_error(client) is None:
    st.stop()

run_tab, html_tab = st.tabs(
    [":material/leaderboard: Interactive run", ":material/description: Classic HTML report"]
)

with run_tab:
    st.caption(
        "Each row is one labeled probe: a query plus its ground-truth relevant "
        "chunk ids (comma separated). Add rows as needed."
    )
    edited = st.data_editor(
        SEED_QUERIES,
        num_rows="dynamic",
        key="arena_editor",
        column_config={
            "query": st.column_config.TextColumn("Query", width="large", required=True),
            "relevant_chunk_ids": st.column_config.TextColumn(
                "Relevant chunk ids", width="medium"
            ),
            "category": st.column_config.TextColumn("Category", width="small"),
        },
    )

    with st.expander("Run settings", expanded=True):
        col_k, col_cand, col_extra = st.columns(3)
        k = col_k.slider("k (cutoff)", min_value=1, max_value=50, value=5)
        candidate_k = col_cand.slider("Candidate depth", min_value=1, max_value=100, value=20)
        include_per_query = col_extra.toggle("Per-query drilldown", value=True)
        ks = st.multiselect("Metric cutoffs (ks)", [1, 3, 5, 10, 20], default=[1, 3, 5])
        pipelines = st.multiselect(
            "Pipelines",
            list(PIPELINE_LABELS.keys()),
            default=list(PIPELINE_LABELS.keys()),
            format_func=lambda name: PIPELINE_LABELS[name],
        )

    if st.button("Run benchmark", type="primary", icon=":material/play_arrow:"):
        queries = _queries_from_editor(edited)
        if not queries:
            st.warning("Add at least one labeled query.")
        elif not pipelines:
            st.warning("Select at least one pipeline.")
        else:
            with st.spinner(
                f"Benchmarking {len(queries)} queries across {len(pipelines)} pipelines..."
            ):
                try:
                    st.session_state["arena_report"] = client.run_arena(
                        queries,
                        k=k,
                        ks=sorted(ks) or [k],
                        pipelines=pipelines,
                        candidate_k=candidate_k,
                        include_per_query=include_per_query,
                    )
                except ApiError as exc:
                    st.session_state.pop("arena_report", None)
                    st.error(str(exc))

    report = st.session_state.get("arena_report")
    if report:
        _render_report(report)

with html_tab:
    st.caption(
        "Server-rendered, self-contained HTML report generated from the live "
        "index via `GET /arena`."
    )
    col_k, col_limit, col_cand = st.columns(3)
    html_k = col_k.number_input("k", min_value=1, max_value=50, value=5)
    html_limit = col_limit.number_input("Probe queries", min_value=1, max_value=50, value=10)
    html_candidate = col_cand.number_input("Candidate depth", min_value=1, max_value=100, value=20)

    if st.button("Generate report", icon=":material/refresh:"):
        with st.spinner("Building report..."):
            try:
                st.session_state["arena_html"] = client.arena_html(
                    k=int(html_k), limit=int(html_limit), candidate_k=int(html_candidate)
                )
            except ApiError as exc:
                st.error(str(exc))

    html = st.session_state.get("arena_html")
    if html:
        components.html(html, height=900, scrolling=True)
