"""
Configuration defaults for the AI Data Analyst.
"""

from dataclasses import dataclass
from pathlib import Path

# Project root: src/utils/config.py -> src/utils -> src -> project
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(slots=True)
class Settings:
    """Application settings."""

    # Gemini (Google AI) — google-genai SDK
    gemini_model: str = "gemini-3.5-flash"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = 768

    # ChromaDB — always resolve against the project, not the process CWD
    chroma_persist_dir: str = str(PROJECT_ROOT / "data" / "chromadb")
    chroma_collection: str = "documents"

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Retrieval
    top_k: int = 5

    # App
    app_title: str = "AI Data Analyst"
    debug: bool = False


# Singleton — import this everywhere
settings = Settings()
