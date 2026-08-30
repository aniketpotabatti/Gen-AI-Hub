"""
ChromaDB vector store wrapper.
Handles embedding storage, similarity search, and collection management.
Uses Google Gemini embeddings via the google-genai SDK.
"""

from __future__ import annotations

import gc
import shutil
from pathlib import Path

import chromadb
import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from google import genai
from google.genai import types

from src.utils.config import settings

_EMBED_BATCH_SIZE = 100


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Custom ChromaDB embedding function using Google Gemini."""

    def __init__(self, api_key: str, model: str | None = None):
        if not api_key:
            raise ValueError("An API key is required to create Gemini embeddings.")
        self.client = genai.Client(api_key=api_key)
        self.model = model or settings.embedding_model
        self.dimension = settings.embedding_dimension

    def name(self) -> str:
        return "gemini-embedding-001"

    def __call__(self, input: Documents) -> Embeddings:
        """Embed a list of documents using Gemini."""
        texts = list(input or [])
        if not texts:
            return []

        embeddings: Embeddings = []
        for start in range(0, len(texts), _EMBED_BATCH_SIZE):
            batch = texts[start : start + _EMBED_BATCH_SIZE]
            result = self.client.models.embed_content(
                model=self.model,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=self.dimension,
                ),
            )
            if not result.embeddings:
                raise RuntimeError("Gemini returned no embeddings for this batch.")
            for item in result.embeddings:
                values = np.asarray(item.values, dtype=np.float32)
                norm = np.linalg.norm(values)
                if norm > 0:
                    values = values / norm
                embeddings.append(values.tolist())
        return embeddings


class VectorStore:
    """Simple ChromaDB wrapper for document storage and retrieval."""

    def __init__(
        self,
        api_key: str | None = None,
        collection_name: str | None = None,
        persist_dir: str | None = None,
    ):
        if not api_key:
            raise ValueError("An API key is required to initialize the vector store.")

        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.collection_name = collection_name or settings.chroma_collection
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.embedding_fn = GeminiEmbeddingFunction(api_key=api_key)
        self.collection = self._open_collection()

    def _open_collection(self):
        try:
            return self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            if not _is_recoverable_chroma_error(exc):
                raise
            gc.collect()
            persist_path = Path(self.persist_dir)
            if persist_path.exists():
                shutil.rmtree(persist_path, ignore_errors=True)
            persist_path.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            return self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )

    def add_documents(self, chunks: list[dict]) -> int:
        """
        Add document chunks to the vector store.

        Args:
            chunks: List of dicts with 'id', 'text', and 'metadata' keys.
                    (Output of doc_processor.document_to_chunks)

        Returns:
            Number of chunks added.
        """
        if not chunks:
            return 0

        ids = [c["id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [_sanitize_metadata(c.get("metadata") or {}) for c in chunks]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        return len(chunks)

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        """
        Search for similar documents.

        Args:
            query: Search query string.
            top_k: Number of results to return.

        Returns:
            List of dicts with 'text', 'metadata', and 'score' keys,
            sorted by relevance (most relevant first).
        """
        count = self.collection.count()
        if count == 0:
            return []

        k = min(top_k or settings.top_k, count)
        results = self.collection.query(
            query_texts=[query],
            n_results=k,
        )

        output = []
        if results and results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            distances = results["distances"][0] if results["distances"] else [0.0] * len(docs)

            for doc, meta, dist in zip(docs, metas, distances):
                output.append(
                    {
                        "text": doc,
                        "metadata": meta or {},
                        "score": round(1 - float(dist), 4),
                    }
                )
        return output

    def get_stats(self) -> dict:
        """Return basic stats about the vector store."""
        return {
            "collection_name": self.collection_name,
            "document_count": self.collection.count(),
            "persist_dir": self.persist_dir,
        }

    def delete_collection(self):
        """Delete the entire collection."""
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def list_sources(self) -> list[str]:
        """List all unique document sources in the store."""
        if self.collection.count() == 0:
            return []

        all_data = self.collection.get(include=["metadatas"])
        sources = set()
        for meta in all_data["metadatas"] or []:
            if meta and "source" in meta:
                sources.add(meta["source"])
        return sorted(sources)


def _sanitize_metadata(metadata: dict) -> dict:
    """Chroma only accepts str, int, float, or bool metadata values."""
    clean = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            clean[str(key)] = value
        else:
            clean[str(key)] = str(value)
    return clean


def _is_recoverable_chroma_error(exc: Exception) -> bool:
    message = str(exc).lower()
    markers = (
        "no such table",
        "schema",
        "dimension",
        "hnsw",
        "corrupt",
        "embedding function",
        "migrations",
        "unique constraint",
    )
    return any(marker in message for marker in markers)
