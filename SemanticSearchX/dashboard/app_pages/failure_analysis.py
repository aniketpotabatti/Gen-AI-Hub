"""Failure Analysis: categorize why a query failed to retrieve its relevant chunks."""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from dashboard.api_client import ApiError
from dashboard.runtime import api_client
from dashboard.ui import (
    CATEGORY_STYLES,
    health_or_error,
    parse_json_object,
    render_page_header,
    split_ids,
)

_ALERT_BY_KIND = {
    "success": st.success,
    "error": st.error,
    "warning": st.warning,
    "info": st.info,
}


def _empty_results() -> pd.DataFrame:
    """Typed empty frame so ``st.data_editor`` can add rows."""
    return pd.DataFrame(
        {
            "chunk_id": pd.Series(dtype="string"),
            "score": pd.Series(dtype="float"),
        }
    )


def _render_diagnosis(diagnosis: Dict[str, Any]) -> None:
    category = str(diagnosis.get("category", "unknown"))
    icon, kind = CATEGORY_STYLES.get(category, (":material/help:", "info"))

    with st.container(horizontal=True):
        st.metric("Category", category.replace("_", " ").title(), border=True)
        st.metric("Confidence", f"{diagnosis.get('confidence', 0.0):.0%}", border=True)

    alert = _ALERT_BY_KIND[kind]
    alert(
        f"**{diagnosis.get('reason', '')}**\n\n"
        f"**Recommended action:** {diagnosis.get('recommended_action', '')}",
        icon=icon,
    )

    diagnostics = diagnosis.get("diagnostics")
    if diagnostics:
        with st.expander("Raw diagnostics"):
            st.json(diagnostics)


render_page_header(
    "Failure Analysis",
    "Diagnose why a query missed its relevant chunks and what to do about it.",
)

client = api_client()
if health_or_error(client) is None:
    st.stop()

with st.form("diagnose_form", border=True):
    query = st.text_input("Query")
    expected_raw = st.text_input(
        "Expected relevant chunk ids",
        placeholder="comma separated, e.g. guide-001, guide-004",
    )
    filter_raw = st.text_input(
        "Applied metadata filter (JSON, optional)",
        placeholder='{"source": "handbook"}',
    )
    st.markdown("**Retrieved results**")
    results_df = st.data_editor(
        _empty_results(),
        num_rows="dynamic",
        key="diagnose_results",
        column_config={
            "chunk_id": st.column_config.TextColumn("chunk_id"),
            "score": st.column_config.NumberColumn("score", format="%.4f"),
        },
    )
    submitted = st.form_submit_button(
        "Diagnose", type="primary", icon=":material/stethoscope:"
    )

if submitted:
    if not query.strip():
        st.warning("Enter a query first.")
    else:
        metadata_filter, error = parse_json_object(filter_raw, field="Metadata filter")
        if error:
            st.error(error)
        else:
            retrieved = [
                {"chunk_id": str(row.chunk_id), "score": float(row.score or 0.0)}
                for row in results_df.itertuples()
                if str(row.chunk_id).strip()
            ]
            with st.spinner("Diagnosing..."):
                try:
                    diagnosis = client.diagnose(
                        query.strip(),
                        retrieved_results=retrieved,
                        expected_relevant_ids=split_ids(expected_raw),
                        applied_metadata_filter=metadata_filter,
                    )
                except ApiError as exc:
                    st.error(str(exc))
                else:
                    _render_diagnosis(diagnosis)
