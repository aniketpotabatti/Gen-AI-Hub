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
            self.vectors = []  # list of np.ndarray
            self.ids = []      # list of ids
        self.id_to_metadata = {}  # map id -> metadata dict
        self.next_id = 0

    def add_vectors(self, vectors: np.ndarray, metadata: Optional[List[Dict[str, Any]]] = None):
        if self.use_faiss:
            # Normalize vectors for cosine similarity
            faiss.normalize_L2(vectors)
            self.index.add(vectors.astype('float32'))
        else:
            for i, vec in enumerate(vectors):
                self.vectors.append(vec.astype('float32'))
                self.ids.append(self.next_id + i)
        if metadata:
            for i, meta in enumerate(metadata):
                doc_id = self.next_id + i
                self.id_to_metadata[doc_id] = meta
        else:
            for i in range(len(vectors)):
                doc_id = self.next_id + i
                self.id_to_metadata[doc_id] = {}
        self.next_id += len(vectors)

    def search(self, query_vector: np.ndarray, k: int = 5) -> Tuple[List[int], List[float], List[Dict[str, Any]]]:
        query_vector = query_vector.astype('float32')
        if self.use_faiss:
            faiss.normalize_L2(query_vector.reshape(1, -1))
            distances, indices = self.index.search(query_vector.reshape(1, -1), k)
            distances = distances[0]
            indices = indices[0]
            # Filter out -1 indices (if not enough results)
            valid = indices != -1
            indices = indices[valid]
            distances = distances[valid]
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
            # Get top k
            top_k_idx = np.argsort(similarities)[::-1][:k]
            indices = [self.ids[i] for i in top_k_idx]
            distances = [similarities[i] for i in top_k_idx]
        metadata = [self.id_to_metadata.get(int(idx), {}) for idx in indices]
        return list(indices), list(distances), metadata

    def save(self, path: str):
        if self.use_faiss:
            faiss.write_index(self.index, os.path.join(path, "index.faiss"))
        else:
            data = {
                "vectors": [v.tolist() for v in self.vectors],
                "ids": self.ids,
                "dimension": self.dimension
            }
            with open(os.path.join(path, "vectors.json"), "w") as f:
                json.dump(data, f)
        with open(os.path.join(path, "metadata.json"), "w") as f:
            json.dump(self.id_to_metadata, f)

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
        if self.id_to_metadata:
            self.next_id = max(self.id_to_metadata.keys()) + 1
        else:
            self.next_id = 0