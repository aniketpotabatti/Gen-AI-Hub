"""Pure input-parsing helpers shared by the dashboard pages.

Deliberately Streamlit-free so they can be unit-tested without importing the UI
runtime.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple


def parse_json_object(
    text: str, *, field: str = "JSON"
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse an optional JSON object typed by the user.

    Returns ``(value, error)``. Empty input yields ``(None, None)``.
    """
    text = (text or "").strip()
    if not text:
        return None, None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"{field} is not valid JSON: {exc}"
    if not isinstance(parsed, dict):
        return None, f"{field} must be a JSON object."
    return parsed, None


def split_ids(raw: str) -> List[str]:
    """Split a comma/whitespace separated id list into tokens."""
    if not raw:
        return []
    return [token for token in re.split(r"[,\s]+", raw) if token]
