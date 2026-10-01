"""SemanticSearchX interactive dashboard - Streamlit entry point.

Run with::

    streamlit run dashboard/streamlit_app.py

The app talks to the FastAPI backend over HTTP (see ``SEMANTICSEARCHX_API_URL``)
and never imports the retrieval core.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the project root importable so ``dashboard.*`` resolves regardless of the
# working directory Streamlit was launched from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from dashboard.runtime import api_client
from dashboard.ui import render_sidebar_status

st.set_page_config(
    page_title="SemanticSearchX",
    page_icon=":material/search_insights:",
    layout="wide",
    initial_sidebar_state="expanded",
)

_PAGES_DIR = Path(__file__).resolve().parent / "app_pages"


def _page(filename: str, title: str, icon: str, **kwargs) -> st.Page:
    """Build an ``st.Page`` from a filename in ``dashboard/app_pages``."""
    return st.Page(str(_PAGES_DIR / filename), title=title, icon=icon, **kwargs)


navigation = st.navigation(
    {
        "Overview": [
            _page("home.py", "Overview", ":material/dashboard:", default=True),
        ],
        "Explore": [
            _page("search_playground.py", "Search Playground", ":material/travel_explore:"),
            _page("corpus_ingest.py", "Corpus & Ingest", ":material/library_books:"),
        ],
        "Evaluate": [
            _page("benchmark_arena.py", "Benchmark Arena", ":material/leaderboard:"),
            _page("failure_analysis.py", "Failure Analysis", ":material/bug_report:"),
        ],
        "Operate": [
            _page("observability.py", "Observability", ":material/monitoring:"),
        ],
    },
    position="sidebar",
)

render_sidebar_status(api_client())

navigation.run()
