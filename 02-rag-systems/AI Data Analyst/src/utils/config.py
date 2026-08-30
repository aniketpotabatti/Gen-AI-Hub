"""
Configuration defaults for the AI Data Analyst.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    """Application settings."""

    # Gemini (Google AI)
    gemini_model: str = "gemini-3.5-flash"
    embedding_model: str = "models/embedding-001"
    embedding_dimension: int = 768

    # ChromaDB
    chroma_persist_dir: str = "./data/chromadb"
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
