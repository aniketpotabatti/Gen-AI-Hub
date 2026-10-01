from typing import List, Union
import hashlib
import numpy as np

class EmbeddingModel:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", dim: int = 384):
        self.model_name = model_name
        self.dim = dim
        self.model = None
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            # Offline / broken env fallback: deterministic hash embeddings so the
            # retrieval pipeline and demo still run. Real embeddings when available.
            print(f"Warning: using HashEmbedding fallback ({e})")
            self.model = None

    def _hash_embed(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vecs = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            # Expand hash bytes to dim floats deterministically.
            vals = []
            counter = 0
            while len(vals) < self.dim:
                d = hashlib.sha256(h + counter.to_bytes(4, "little")).digest()
                vals.extend(b / 255.0 for b in d)
                counter += 1
            v = np.array(vals[: self.dim], dtype=np.float32)
            v = v - v.mean()
            n = np.linalg.norm(v)
            vecs.append(v / (n + 1e-10))
        return np.stack(vecs)

    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return np.zeros((0, self.get_dimension()), dtype=np.float32)
        if self.model is not None:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return np.asarray(embeddings, dtype=np.float32)
        return self._hash_embed(texts)

    def get_dimension(self) -> int:
        if self.model is not None:
            return self.model.get_sentence_embedding_dimension()
        return self.dim