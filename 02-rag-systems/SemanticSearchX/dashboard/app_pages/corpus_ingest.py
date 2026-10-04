"""Corpus & Ingest: browse the indexed chunks and add new ones."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from dashboard.api_client import ApiError
from dashboard.runtime import api_client
from dashboard.ui import health_or_error, render_page_header

EXAMPLE_PAYLOAD = json.dumps(
    [
        {
            "chunk_id": "guide-001",
            "text": "SemanticSearchX fuses dense and sparse retrieval before reranking.",
            "metadata": {"source": "guide"},
        }
    ],
    indent=2,
)


def _preview(text: str, width: int = 120) -> str:
    collapsed = " ".join((text or "").split())
    return collapsed if len(collapsed) <= width else collapsed[: width - 1] + "\u2026"


def _chunks_from_json(text: str) -> List[Dict[str, Any]]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    if not isinstance(parsed, list) or not parsed:
        raise ValueError("Provide a non-empty JSON list of chunks.")
    for chunk in parsed:
        if not isinstance(chunk, dict) or "chunk_id" not in chunk or "text" not in chunk:
            raise ValueError("Each chunk needs at least 'chunk_id' and 'text'.")
    return parsed


def _chunks_from_file(name: str, content: str) -> List[Dict[str, Any]]:
    if name.lower().endswith(".json"):
        return _chunks_from_json(content)
    stem = Path(name).stem
    blocks = [block.strip() for block in re.split(r"\n\s*\n", content) if block.strip()]
    if not blocks:
        raise ValueError("The uploaded file contained no text.")
    return [
        {"chunk_id": f"{stem}-{i:03d}", "text": block, "metadata": {"source": name}}
        for i, block in enumerate(blocks, start=1)
    ]


render_page_header(
    "Corpus & Ingest",
    "Inspect what is currently indexed and add new chunks to the live index.",
)

client = api_client()
if health_or_error(client) is None:
    st.stop()

browse_tab, ingest_tab = st.tabs(
    [":material/library_books: Browse", ":material/library_add: Ingest"]
)

with browse_tab:
    col_filter, col_size, col_page = st.columns([2, 1, 1])
    text_filter = col_filter.text_input("Filter", placeholder="substring match on id or text")
    page_size = col_size.number_input("Page size", min_value=10, max_value=200, value=25, step=5)
    page_number = col_page.number_input("Page", min_value=1, value=1, step=1)
    offset = (int(page_number) - 1) * int(page_size)

    try:
        data = client.corpus(limit=int(page_size), offset=offset, q=text_filter.strip() or None)
    except ApiError as exc:
        st.error(str(exc))
        st.stop()

    chunks = data.get("chunks", [])
    st.caption(f"{data.get('total', 0):,} matching chunks (showing {len(chunks)})")

    if not chunks:
        st.info("Nothing to show. Index chunks on the **Ingest** tab first.")
    else:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "chunk_id": chunk["chunk_id"],
                        "chars": len(chunk.get("text", "")),
                        "preview": _preview(chunk.get("text", "")),
                    }
                    for chunk in chunks
                ]
            ),
            hide_index=True,
            height=260,
        )
        selected_id = st.selectbox("Inspect chunk", [c["chunk_id"] for c in chunks])
        selected = next(c for c in chunks if c["chunk_id"] == selected_id)
        st.code(selected.get("text", ""), language=None)
        st.json(selected.get("metadata", {}))

with ingest_tab:
    st.caption(
        "Paste a JSON list of `{chunk_id, text, metadata}` objects, or upload a "
        "`.json` file. `.txt`/`.md` files are split into paragraph chunks."
    )
    raw = st.text_area("Chunks (JSON)", value=EXAMPLE_PAYLOAD, height=220)
    uploaded = st.file_uploader("...or upload a file", type=["json", "txt", "md"])

    if st.button("Index chunks", type="primary", icon=":material/library_add:"):
        try:
            if uploaded is not None:
                chunks = _chunks_from_file(
                    uploaded.name, uploaded.getvalue().decode("utf-8", errors="replace")
                )
            else:
                chunks = _chunks_from_json(raw)
        except ValueError as exc:
            st.error(str(exc))
        else:
            with st.spinner(f"Indexing {len(chunks)} chunk(s)..."):
                try:
                    result = client.index_chunks(chunks)
                except ApiError as exc:
                    st.error(str(exc))
                else:
                    st.success(
                        f"Indexed {result.get('indexed_count', 0)} chunks · "
                        f"total {result.get('total_indexed', 0)} · "
                        f"{result.get('duration_ms', 0)} ms"
                    )
