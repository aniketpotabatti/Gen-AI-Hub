"""Observability: live engine health and Prometheus metrics."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

from dashboard.api_client import ApiError
from dashboard.runtime import api_client
from dashboard.ui import health_or_error, render_page_header

_SAMPLE_RE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)"
    r"(?:\{(?P<labels>[^}]*)\})?\s+"
    r"(?P<value>[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?)$"
)


def parse_prometheus(text: str) -> Dict[str, List[Tuple[str, float]]]:
    """Group Prometheus exposition text into ``{metric: [(labels, value)]}``."""
    families: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _SAMPLE_RE.match(line)
        if match:
            families[match.group("name")].append(
                (match.group("labels") or "", float(match.group("value")))
            )
    return dict(families)


render_page_header("Observability", "Live engine health and Prometheus metrics.")

client = api_client()
auto_refresh = st.toggle("Auto-refresh every 5s", value=False)


@st.fragment(run_every="5s" if auto_refresh else None)
def _live_view() -> None:
    """Health KPIs and parsed metrics; optionally auto-refreshing."""
    health = health_or_error(client)
    if health is None:
        return

    cache = health.get("cache_status", {}) or {}
    with st.container(horizontal=True):
        st.metric("Status", str(health.get("status", "unknown")).title(), border=True)
        st.metric("Indexed chunks", f"{health.get('indexed_chunks', 0):,}", border=True)
        st.metric("Cache backend", str(cache.get("backend", "?")), border=True)
        st.metric("Cache hit rate", f"{cache.get('hit_rate', 0.0):.0%}", border=True)

    try:
        families = parse_prometheus(client.metrics_text())
    except ApiError as exc:
        st.error(str(exc))
        return

    if not families:
        st.info("No metrics reported yet - issue a few queries first.")
        return

    summary = pd.DataFrame(
        [
            {
                "metric": name,
                "series": len(samples),
                "total": round(sum(value for _, value in samples), 4),
            }
            for name, samples in sorted(families.items())
        ]
    )

    with st.container(border=True):
        st.markdown("**Busiest metric families**")
        st.bar_chart(
            summary.sort_values("total", ascending=False).head(12),
            x="metric",
            y="total",
            horizontal=True,
        )

    with st.container(border=True):
        st.markdown("**All metrics**")
        st.dataframe(summary, hide_index=True, height=280)

    with st.expander("Raw samples"):
        for name, samples in sorted(families.items()):
            st.markdown(f"`{name}`")
            st.dataframe(
                pd.DataFrame(
                    [{"labels": labels, "value": value} for labels, value in samples]
                ),
                hide_index=True,
            )


_live_view()
