#!/usr/bin/env python3
"""
Phase 1 Demo: Retrieval Foundation
- Document ingestion
- Chunking
- Embedding generation
- Vector indexing
- Top-k similarity search
- Metadata filtering
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "SemanticSearchX"))

from ingestion.base import ingest_directory, Document
from chunking.base import RecursiveCharacterChunker
from embeddings.base import EmbeddingModel
from dense_retrieval.base import VectorStore
from utils.helpers import ensure_dir

def main():
    # 1. Ingest documents
    data_dir = os.path.join(os.path.dirname(__file__), "sample_data")
    ensure_dir(data_dir)
    # Create a sample file if none exists
    sample_path = os.path.join(data_dir, "sample.txt")
    if not os.path.exists(sample_path):
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write("""This is a sample document about artificial intelligence.
AI is the simulation of human intelligence in machines.
Machine learning is a subset of AI that enables systems to learn from data.
Deep learning uses neural networks with many layers.
Natural language processing helps computers understand human language.
Computer vision enables machines to interpret visual information.
""")
    print("Ingesting documents...")
    docs: List[Document] = ingest_directory(data_dir)
    print(f"Ingested {len(docs)} documents.")
    for i, doc in enumerate(docs):
        print(f"  Doc {i}: length={len(doc.content)}")

    # 2. Chunking
    print("\nChunking documents...")
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=20)
    all_chunks = []
    chunk_metadata = []  # metadata for each chunk
    for doc_idx, doc in enumerate(docs):
        chunks = chunker.chunk_text(doc.content)
        for chunk_idx, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            chunk_metadata.append({
                "source_doc": doc_idx,
                "chunk_id": chunk_idx,
                "source": doc.metadata.get("source", ""),
                "content": chunk[:50] + "..."  # preview
            })
    print(f"Created {len(all_chunks)} chunks.")

    # 3. Embedding generation
    print("\nGenerating embeddings...")
    embed_model = EmbeddingModel()
    embeddings = embed_model.encode(all_chunks)
    print(f"Embeddings shape: {embeddings.shape}")

    # 4. Vector indexing
    print("\nBuilding vector index...")
    vector_store = VectorStore(dimension=embed_model.get_dimension())
    vector_store.add_vectors(embeddings, metadata=chunk_metadata)
    print(f"Indexed {vector_store.next_id} vectors.")

    # 5. Save index
    index_dir = os.path.join(os.path.dirname(__file__), "vector_index")
    ensure_dir(index_dir)
    vector_store.save(index_dir)
    print(f"Saved index to {index_dir}")

    # 6. Search demo
    print("\n--- Search Demo ---")
    queries = [
        "What is machine learning?",
        "Tell me about deep learning",
        "How does NLP work?"
    ]
    for query in queries:
        print(f"\nQuery: {query}")
        q_emb = embed_model.encode([query])
        indices, scores, metas = vector_store.search(q_emb[0], k=3)
        for idx, (score, meta) in enumerate(zip(scores, metas)):
            print(f"  Result {idx+1}: score={score:.4f}")
            print(f"    Source: {meta.get('source', 'unknown')}")
            print(f"    Chunk preview: {meta.get('content', '')}")

if __name__ == "__main__":
    main()