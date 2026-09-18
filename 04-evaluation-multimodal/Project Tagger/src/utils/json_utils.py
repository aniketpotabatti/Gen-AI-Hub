"""Tolerant JSON extraction for raw VLM responses.

VLMs frequently wrap JSON in markdown fences, add commentary, or emit
Python-style literals (single quotes, trailing commas); these helpers
recover the payload defensively instead of failing the request.
"""

import ast
import json
from typing import Any


def extract_json_block(text: str) -> str:
    """Strip markdown fences / commentary, returning the JSON payload."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()[1:]  # drop opening fence (```json or ```)
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        return cleaned[start : end + 1]
    # If we found an opening brace but no closing brace, attempt to close it.
    if start != -1 and end == -1:
        # Assume the rest after start is the JSON content; add a closing brace.
        return cleaned[start:] + "}"
    # No braces at all -> return as-is to let parse_json_payload raise appropriately.
    return cleaned


def parse_json_payload(text: str) -> Any:
    """Parse a raw (possibly fenced/commented) response into Python objects.

    Falls back to `ast.literal_eval` (safe: parses literals, never executes
    code) for Python-style output such as single-quoted keys or trailing
    commas, which strict `json.loads` rejects.
    """
    cleaned = extract_json_block(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    try:
        return ast.literal_eval(cleaned)
    except (ValueError, SyntaxError) as exc:
        raise ValueError(f"Response is not valid JSON: {exc}") from exc

