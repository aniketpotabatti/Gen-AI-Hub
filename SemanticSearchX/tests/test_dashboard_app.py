"""Smoke tests: every dashboard page renders without raising an exception.

Streamlit is only installed in the dashboard's own environment, so the whole
module is skipped when it is unavailable (e.g. in the API-only environment).
"""
from pathlib import Path

import pytest

try:  # Streamlit is a dashboard-only dependency.
    import streamlit  # noqa: F401
except ImportError:
    pytest.skip(
        "Streamlit is not installed (dashboard-only dependency)",
        allow_module_level=True,
    )

from streamlit.testing.v1 import AppTest  # noqa: E402

_APP_PAGES = Path(__file__).resolve().parent.parent / "dashboard" / "app_pages"

PAGE_FILES = [
    "home.py",
    "search_playground.py",
    "corpus_ingest.py",
    "benchmark_arena.py",
    "failure_analysis.py",
    "observability.py",
]


@pytest.mark.parametrize("page_file", PAGE_FILES)
def test_page_renders_without_exception(page_file):
    """Each page must render standalone (the API is offline in this test)."""
    at = AppTest.from_file(str(_APP_PAGES / page_file), default_timeout=60).run()
    assert not at.exception, [element.value for element in at.exception]


def test_entry_point_renders_without_exception():
    """The navigation entry point must load its default page cleanly."""
    entry = _APP_PAGES.parent / "streamlit_app.py"
    at = AppTest.from_file(str(entry), default_timeout=60).run()
    assert not at.exception, [element.value for element in at.exception]
