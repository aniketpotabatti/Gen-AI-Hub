"""Interactive Streamlit dashboard for SemanticSearchX.

A thin, read-mostly UI layer that talks to the FastAPI backend over HTTP. It
deliberately avoids importing the retrieval core, so it can run in a
lightweight Python environment without Torch / FAISS / Qdrant / Redis.
"""
