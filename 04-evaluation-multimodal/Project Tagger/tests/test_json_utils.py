"""Tolerant JSON parsing for raw VLM responses."""

import pytest

from src.utils.json_utils import extract_json_block, parse_json_payload


def test_extracts_from_markdown_fences():
    payload = '```json\n{"category": "apparel"}\n```'
    assert parse_json_payload(payload) == {"category": "apparel"}


def test_extracts_from_surrounding_commentary():
    payload = 'Here are the tags:\n{"category": "apparel"}\nHope this helps!'
    assert parse_json_payload(payload) == {"category": "apparel"}


def test_parses_single_quoted_python_dict():
    """Regression: Gemini emitted single-quoted 'JSON' -> JSONDecodeError."""
    payload = "{\n    'category': 'apparel',\n    'color': ['blue']\n}"
    assert parse_json_payload(payload) == {"category": "apparel", "color": ["blue"]}


def test_parses_trailing_comma():
    payload = '{"category": "apparel",}'
    assert parse_json_payload(payload) == {"category": "apparel"}


def test_raises_value_error_on_garbage():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_json_payload("totally not json at all")


def test_extract_json_block_returns_innermost_braces():
    assert extract_json_block("noise {\"a\": 1} more") == '{"a": 1}'
