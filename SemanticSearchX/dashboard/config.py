"""Configuration for the SemanticSearchX dashboard (UI layer only)."""
from __future__ import annotations

import os

# Base URL of the SemanticSearchX FastAPI backend.
DEFAULT_API_URL = "http://localhost:8000"

# Per-request timeout in seconds. Benchmark runs can be slow, so the default is
# generous; override with SEMANTICSEARCHX_DASHBOARD_TIMEOUT.
DEFAULT_TIMEOUT_SECONDS = 120.0


def api_base_url() -> str:
    """Resolve the backend base URL from the environment."""
    return os.getenv("SEMANTICSEARCHX_API_URL", DEFAULT_API_URL).rstrip("/")


def request_timeout() -> float:
    """Resolve the HTTP timeout (seconds) from the environment."""
    raw = os.getenv("SEMANTICSEARCHX_DASHBOARD_TIMEOUT")
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
