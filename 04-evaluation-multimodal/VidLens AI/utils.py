"""
utils.py — Stateless helper utilities for VidLens AI.

Responsibilities:
- Video upload to the Gemini File API (with ACTIVE-state polling)
- Web search result formatting
"""

from __future__ import annotations

import io
import time
from pathlib import Path

# MIME types for all supported video formats
MIME_TYPES: dict[str, str] = {
    ".mp4":  "video/mp4",
    ".mov":  "video/quicktime",
    ".avi":  "video/x-msvideo",
    ".mkv":  "video/x-matroska",
    ".webm": "video/webm",
}

_POLL_INTERVAL = 3       # seconds between state-checks
_MAX_POLL_ATTEMPTS = 60  # 60 × 3 s = 3 min maximum wait


def _mime_type(file_name: str) -> str:
    """Resolve MIME type from file extension; default to video/mp4."""
    return MIME_TYPES.get(Path(file_name).suffix.lower(), "video/mp4")


def upload_video_to_gemini(client, video_bytes: bytes, file_name: str) -> object:
    """
    Upload *video_bytes* to the Gemini File API and block until ACTIVE.

    Args:
        client:      Initialised ``google.genai.Client``.
        video_bytes: Raw video data.
        file_name:   Original filename — used only for MIME detection and display name.

    Returns:
        The Gemini ``File`` object in ACTIVE state.

    Raises:
        RuntimeError: On processing failure or timeout.
    """
    # SDK requires a file-like object, not raw bytes
    file_obj = io.BytesIO(video_bytes)

    gemini_file = client.files.upload(
        file=file_obj,
        config={"mime_type": _mime_type(file_name), "display_name": file_name},
    )

    # Poll until the file is ready (server-side transcoding)
    for attempt in range(_MAX_POLL_ATTEMPTS):
        state = gemini_file.state.name
        if state == "ACTIVE":
            return gemini_file
        if state == "FAILED":
            raise RuntimeError(f"Gemini video processing failed (state={state}).")
        time.sleep(_POLL_INTERVAL)
        gemini_file = client.files.get(name=gemini_file.name)

    raise RuntimeError("Video processing timed out — try a shorter clip.")


def format_search_results(results: list[dict]) -> str:
    """
    Render DuckDuckGo results as a concise markdown context block.

    Args:
        results: List of dicts with keys ``title``, ``href``, ``body``.

    Returns:
        Prompt-ready string, or an empty string when *results* is empty.
    """
    if not results:
        return ""

    lines = ["### 🌐 Web Search Context\n"]
    for i, r in enumerate(results, start=1):
        title = r.get("title", "Untitled")
        url   = r.get("href", "")
        body  = r.get("body", "").strip()
        lines.append(f"**[{i}] {title}**")
        if url:
            lines.append(f"Source: {url}")
        if body:
            lines.append(f"{body}\n")

    return "\n".join(lines)
