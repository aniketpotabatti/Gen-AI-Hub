"""Phase 1 regression tests: ingestion, chunking, vector store."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chunking.base import RecursiveCharacterChunker
from dense_retrieval.base import VectorStore
from ingestion.base import ingest_directory


def test_chunker_rejects_bad_overlap():
    with pytest.raises(ValueError):
        RecursiveCharacterChunker(chunk_size=50, chunk_overlap=50)
    with pytest.raises(ValueError):
        RecursiveCharacterChunker(chunk_size=50, chunk_overlap=60)


def test_chunker_empty_and_terminates():
    c = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=20)
    assert c.chunk_text("") == []
    chunks = c.chunk_text("a" * 250)
    assert len(chunks) == 3
    assert "".join(chunks[i][:80] for i in range(3))


def test_ingest_skips_empty_and_assigns_ids(tmp_path):
    (tmp_path / "empty.txt").write_text("   \n", encoding="utf-8")
    (tmp_path / "good.txt").write_text("hello world", encoding="utf-8")
    docs = ingest_directory(str(tmp_path))
    assert len(docs) == 1
    assert docs[0].id is not None
    assert docs[0].metadata["content_hash"]


def test_vector_store_no_caller_mutation():
    vs = VectorStore(dimension=4, use_faiss=True)
    v = np.random.rand(3, 4).astype(np.float32)
    orig = v.copy()
    vs.add_vectors(v)
    assert not (v != orig).any()
    q = np.random.rand(4).astype(np.float32)
    q0 = q.copy()
    vs.search(q, k=2)
    assert not (q != q0).any()


def test_vector_store_metadata_filter_and_delete():
    vs = VectorStore(dimension=4, use_faiss=False)
    rng = np.random.default_rng(0)
    vecs = rng.random((4, 4), dtype=np.float32)
    metas = [
        {"source": "a.txt", "doc_hash": "h1", "chunk_id": "h1::chunk-0"},
        {"source": "a.txt", "doc_hash": "h1", "chunk_id": "h1::chunk-1"},
        {"source": "b.txt", "doc_hash": "h2", "chunk_id": "h2::chunk-0"},
        {"source": "b.txt", "doc_hash": "h2", "chunk_id": "h2::chunk-1"},
    ]
    vs.add_vectors(vecs, metadata=metas)
    q = rng.random(4, dtype=np.float32)
    _, _, got = vs.search(q, k=4, metadata_filter={"source": "b.txt"})
    assert got and all(m["source"] == "b.txt" for m in got)
    assert vs.delete_by_filter({"source": "a.txt"}) == 2
    _, _, rest = vs.search(q, k=4)
    assert all(m["source"] == "b.txt" for m in rest)


def test_vector_store_faiss_delete_keeps_right_vectors():
    # Regression: deleting id 0 must not shift/drop the wrong FAISS vectors.
    vs = VectorStore(dimension=2, use_faiss=True)
    vecs = np.array([[1, 0], [0, 1], [1, 1], [0.5, 0.5]], dtype=np.float32)
    vs.add_vectors(vecs, metadata=[{"chunk_id": f"c{i}"} for i in range(4)])
    assert vs.delete_by_filter({"chunk_id": "c0"}) == 1
    assert [m["chunk_id"] for _, m in sorted(vs.id_to_metadata.items())] == ["c1", "c2", "c3"]
    q = np.array([0, 1], dtype=np.float32)
    _, scores, metas = vs.search(q, k=3)
    assert metas[0]["chunk_id"] == "c1"
    assert scores[0] == max(scores)
    assert vs.delete_by_filter({"chunk_id": "c2"}) == 1
    assert [m["chunk_id"] for _, m in sorted(vs.id_to_metadata.items())] == ["c1", "c3"]


def test_embedding_encode_empty():
    from embeddings.base import EmbeddingModel

    m = EmbeddingModel.__new__(EmbeddingModel)
    m.model = None
    m.dim = 8
    assert m.encode([]).shape == (0, 8)


def test_hybrid_index_chunks_skips_all_duplicates():
    from hybrid_retrieval.fusion import HybridRetriever
    from sparse_retrieval.bm25 import BM25Index
    from sparse_retrieval.exact_match import ExactMatchIndex

    vs = VectorStore(dimension=4, use_faiss=False)
    bm25, exact = BM25Index(), ExactMatchIndex()
    hy = HybridRetriever(vs, bm25, exact, None)
    vecs = np.zeros((2, 4), dtype=np.float32)
    assert hy.index_chunks(["t1", "t2"], [{"chunk_id": "a"}, {"chunk_id": "b"}], vecs) == 2
    assert hy.index_chunks(["t1", "t2"], [{"chunk_id": "a"}, {"chunk_id": "b"}], vecs) == 0
    assert len(vs.id_to_metadata) == 2 and len(bm25) == 2 and len(exact) == 2
    with __import__("pytest").raises(ValueError):
        hy.index_chunks(["t1"], [{"chunk_id": "a"}], vecs)


def test_vector_store_save_load_roundtrip(tmp_path):
    vs = VectorStore(dimension=4, use_faiss=True)
    rng = np.random.default_rng(1)
    vecs = rng.random((3, 4), dtype=np.float32)
    vs.add_vectors(vecs, metadata=[{"doc_hash": "h", "chunk_id": f"h::chunk-{i}"} for i in range(3)])
    vs.save(str(tmp_path))
    vs2 = VectorStore(dimension=4, use_faiss=True)
    vs2.load(str(tmp_path))
    assert vs2.next_id == 3
    assert all(isinstance(k, int) for k in vs2.id_to_metadata)
    assert vs2.is_indexed("h")
    q = rng.random(4, dtype=np.float32)
    idx, scores, metas = vs2.search(q, k=2)
    assert len(idx) == 2
