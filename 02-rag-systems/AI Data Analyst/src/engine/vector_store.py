"""
ChromaDB vector store wrapper.
Handles embedding storage, similarity search, and collection management.
Uses Google Gemini embeddings.
"""

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from google import genai

from src.utils.config import settings


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Custom ChromaDB embedding function using Google Gemini."""

    def __init__(self, api_key: str, model: str | None = None):
        if not api_key:
            raise ValueError("An API key is required to create Gemini embeddings.")
        self.client = genai.Client(api_key=api_key)
        self.model = model or settings.embedding_model

    def __call__(self, input: Documents) -> Embeddings:
        """Embed a list of documents using Gemini."""
        embeddings = []
        for text in input:
            result = self.client.models.embed_content(
                model=self.model,
                content=text,
            )
            embeddings.append(result.embeddings[0].values)
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

        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(path=self.persist_dir)

        # Use Gemini embeddings
        self.embedding_fn = GeminiEmbeddingFunction(api_key=api_key)

        # Get or create collection safely (handles legacy/corrupted DB migration errors)
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            import gc
            import shutil
            from pathlib import Path

            gc.collect()
            p = Path(self.persist_dir)
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            self.collection = self.client.get_or_create_collection(
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
        metadatas = [c["metadata"] for c in chunks]

        # ChromaDB handles embedding automatically via the embedding function
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
        k = top_k or settings.top_k

        results = self.collection.query(
            query_texts=[query],
            n_results=min(k, self.collection.count()) if self.collection.count() > 0 else k,
        )

        # Flatten ChromaDB's nested response format
        output = []
        if results and results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            distances = results["distances"][0] if results["distances"] else [0.0] * len(docs)

            for doc, meta, dist in zip(docs, metas, distances):
                output.append(
                    {
                        "text": doc,
                        "metadata": meta,
                        "score": round(1 - dist, 4),  # Convert distance to similarity
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
        self.client.delete_collection(self.collection_name)
        # Recreate empty collection
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
        for meta in all_data["metadatas"]:
            if meta and "source" in meta:
                sources.add(meta["source"])
        return sorted(sources)
