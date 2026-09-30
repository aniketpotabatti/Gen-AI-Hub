import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import json
import os

try:
    import faiss
except ImportError:
    faiss = None

class VectorStore:
    def __init__(self, dimension: int, use_faiss: bool = True):
        self.dimension = dimension
        self.use_faiss = use_faiss and faiss is not None
        if self.use_faiss:
            self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine after normalization)
        else:
            self.vectors: List[np.ndarray] = []
            self.ids: List[int] = []
        self.id_to_metadata: Dict[int, Dict[str, Any]] = {}
        self.indexed_doc_hashes: set = set()
        self.next_id = 0

    def __len__(self) -> int:
        return self.next_id

    def add_vectors(self, vectors: np.ndarray, metadata: Optional[List[Dict[str, Any]]] = None) -> List[int]:
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        if len(vectors) == 0:
            return []
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Expected vectors of dimension {self.dimension}, got {vectors.shape[1]}")
        if metadata is not None and len(metadata) != len(vectors):
            raise ValueError("metadata length must match number of vectors")
        ids = list(range(self.next_id, self.next_id + len(vectors)))
        if self.use_faiss:
            # Copy before normalizing: faiss.normalize_L2 works in-place and
            # would otherwise mutate the caller's embeddings array.
            to_add = np.ascontiguousarray(vectors, dtype=np.float32).copy()
            faiss.normalize_L2(to_add)
            self.index.add(to_add)
        else:
            for i, vec in enumerate(vectors):
                self.vectors.append(vec.astype('float32'))
                self.ids.append(self.next_id + i)
        if metadata:
            for i, meta in enumerate(metadata):
                self.id_to_metadata[self.next_id + i] = meta
                h = meta.get("doc_hash")
                if h:
                    self.indexed_doc_hashes.add(h)
        else:
            for i in range(len(vectors)):
                doc_id = self.next_id + i
                self.id_to_metadata[doc_id] = {}
        self.next_id += len(vectors)
        return ids

    def is_indexed(self, doc_hash: str) -> bool:
        """Check whether a document content-hash is already indexed."""
        return doc_hash in self.indexed_doc_hashes

    @staticmethod
    def _matches(meta: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        if not filters:
            return True
        for k, v in filters.items():
            if meta.get(k) != v:
                return False
        return True

    def search(self, query_vector: np.ndarray, k: int = 5, metadata_filter: Optional[Dict[str, Any]] = None) -> Tuple[List[int], List[float], List[Dict[str, Any]]]:
        query_vector = np.ascontiguousarray(query_vector, dtype=np.float32).copy()
        if self.use_faiss:
            if self.next_id == 0:
                return [], [], []
            fetch_k = k if not metadata_filter else min(self.next_id, max(k * 5, k + 10))
            faiss.normalize_L2(query_vector.reshape(1, -1))
            distances, indices = self.index.search(query_vector.reshape(1, -1), fetch_k)
            distances = distances[0]
            indices = indices[0]
            # Filter out -1 indices (if not enough results)
            valid = indices != -1
            indices = indices[valid]
            distances = distances[valid]
            if metadata_filter:
                kept_idx, kept_dist = [], []
                for idx, dist in zip(indices, distances):
                    if self._matches(self.id_to_metadata.get(int(idx), {}), metadata_filter):
                        kept_idx.append(int(idx))
                        kept_dist.append(float(dist))
                        if len(kept_idx) == k:
                            break
                indices, distances = kept_idx, kept_dist
            else:
                indices = [int(i) for i in indices[:k]]
                distances = [float(d) for d in distances[:k]]
        else:
            if not self.vectors:
                return [], [], []
            # Compute cosine similarity
            vecs = np.stack(self.vectors)
            # Normalize
            norm_q = np.linalg.norm(query_vector)
            norm_vecs = np.linalg.norm(vecs, axis=1)
            if norm_q == 0:
                similarities = np.zeros(len(vecs))
            else:
                similarities = np.dot(vecs, query_vector) / (norm_vecs * norm_q + 1e-10)
            # Get top k (with optional metadata filtering)
            order = np.argsort(similarities)[::-1]
            indices, distances = [], []
            for pos in order:
                meta = self.id_to_metadata.get(self.ids[pos], {})
                if self._matches(meta, metadata_filter):
                    indices.append(self.ids[pos])
                    distances.append(float(similarities[pos]))
                    if len(indices) == k:
                        break
        metadata = [self.id_to_metadata.get(int(idx), {}) for idx in indices]
        return list(indices), list(distances), metadata

    def delete_by_filter(self, filters: Dict[str, Any]) -> int:
        """Remove entries matching metadata filters. FAISS path rebuilds the index."""
        to_delete = {i for i, m in self.id_to_metadata.items() if self._matches(m, filters)}
        if not to_delete:
            return 0
        if self.use_faiss:
            ntotal = self.index.ntotal
            all_vecs = np.zeros((ntotal, self.dimension), dtype=np.float32)
            if ntotal:
                import numpy as _np

                keys = _np.arange(ntotal, dtype=_np.int64)
                try:
                    out = self.index.reconstruct_batch(keys)
                    all_vecs[:] = _np.ascontiguousarray(out, dtype=_np.float32)
                except Exception:
                    for p in range(ntotal):
                        all_vecs[p] = self.index.reconstruct(int(p))
            # FAISS positions shift left when earlier ids are removed, so map
            # old position -> surviving vector explicitly (position != id).
            keep = [p for p in range(ntotal) if p not in to_delete]
            kept_vecs = all_vecs[keep] if keep else np.zeros((0, self.dimension), dtype=np.float32)
            self.index = faiss.IndexFlatIP(self.dimension)
            if keep:
                self.index.add(np.ascontiguousarray(kept_vecs))
            survivors = sorted(set(self.id_to_metadata) - to_delete)
            self.id_to_metadata = {n: self.id_to_metadata[o] for n, o in enumerate(survivors)}
            self.next_id = len(survivors)
            self.indexed_doc_hashes = {
                m.get("doc_hash") for m in self.id_to_metadata.values() if m.get("doc_hash")
            }
        else:
            keep = [(i, v) for i, v in zip(self.ids, self.vectors) if i not in to_delete]
            self.ids = [i for i, _ in keep]
            self.vectors = [v for _, v in keep]
            for i in to_delete:
                self.id_to_metadata.pop(i, None)
        return len(to_delete)

    def save(self, path: str):
        os.makedirs(path, exist_ok=True)
        if self.use_faiss:
            faiss.write_index(self.index, os.path.join(path, "index.faiss"))
        else:
            data = {
                "vectors": [v.tolist() for v in self.vectors],
                "ids": self.ids,
                "dimension": self.dimension,
            }
            with open(os.path.join(path, "vectors.json"), "w") as f:
                json.dump(data, f)
        with open(os.path.join(path, "metadata.json"), "w") as f:
            json.dump({str(k): v for k, v in self.id_to_metadata.items()}, f)
        with open(os.path.join(path, "index_state.json"), "w") as f:
            json.dump(
                {"next_id": self.next_id, "doc_hashes": sorted(self.indexed_doc_hashes)}, f
            )

    def load(self, path: str):
        if self.use_faiss:
            self.index = faiss.read_index(os.path.join(path, "index.faiss"))
        else:
            with open(os.path.join(path, "vectors.json"), "r") as f:
                data = json.load(f)
            self.vectors = [np.array(v, dtype='float32') for v in data["vectors"]]
            self.ids = data["ids"]
            self.dimension = data["dimension"]
        with open(os.path.join(path, "metadata.json"), "r") as f:
            self.id_to_metadata = json.load(f)
        # JSON object keys are always strings; convert back to int ids.
        self.id_to_metadata = {int(k): v for k, v in self.id_to_metadata.items()}
        state_path = os.path.join(path, "index_state.json")
        if os.path.exists(state_path):
            with open(state_path, "r") as f:
                state = json.load(f)
            self.next_id = state.get("next_id", 0)
            self.indexed_doc_hashes = set(state.get("doc_hashes", []))
        elif self.id_to_metadata:
            self.next_id = max(self.id_to_metadata.keys()) + 1
            self.indexed_doc_hashes = {
                m.get("doc_hash") for m in self.id_to_metadata.values() if m.get("doc_hash")
            }
        else:
            self.next_id = 0
            self.indexed_doc_hashes = set()