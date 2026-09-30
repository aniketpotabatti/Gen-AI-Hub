"""Qdrant production vector store adapter for SemanticSearchX."""
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

try:
    import qdrant_client
    from qdrant_client.http import models as rest_models
    QDRANT_AVAILABLE = True
except ImportError:
    qdrant_client = None
    rest_models = None
    QDRANT_AVAILABLE = False


class QdrantVectorStore:
    """Production vector store implementation backed by Qdrant (in-memory or server)."""

    def __init__(
        self,
        dimension: int = 384,
        collection_name: str = "semantic_chunks",
        location: str = ":memory:",
        host: Optional[str] = None,
        port: int = 6333,
    ):
        if not QDRANT_AVAILABLE:
            raise ImportError(
                "qdrant-client is required for QdrantVectorStore. Install with `pip install qdrant-client`."
            )
        self.dimension = dimension
        self.collection_name = collection_name
        self.next_id = 0
        self.id_to_metadata: Dict[int, Dict[str, Any]] = {}
        self.indexed_doc_hashes: set = set()

        if host:
            self.client = qdrant_client.QdrantClient(host=host, port=port)
        else:
            self.client = qdrant_client.QdrantClient(location=location)

        # Create collection if it does not exist
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=rest_models.VectorParams(
                    size=self.dimension,
                    distance=rest_models.Distance.COSINE,
                ),
            )

    def __len__(self) -> int:
        return self.next_id

    def is_indexed(self, doc_hash: str) -> bool:
        return doc_hash in self.indexed_doc_hashes

    def add_vectors(
        self,
        vectors: np.ndarray,
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> List[int]:
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        if len(vectors) == 0:
            return []
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Expected vectors of dimension {self.dimension}, got {vectors.shape[1]}")
        if metadata is not None and len(metadata) != len(vectors):
            raise ValueError("metadata length must match number of vectors")

        points = []
        ids = []
        for i, vec in enumerate(vectors):
            point_id = self.next_id + i
            meta = metadata[i] if metadata else {}
            self.id_to_metadata[point_id] = meta
            h = meta.get("doc_hash")
            if h:
                self.indexed_doc_hashes.add(h)

            points.append(
                rest_models.PointStruct(
                    id=point_id,
                    vector=vec.tolist(),
                    payload=meta,
                )
            )
            ids.append(point_id)

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        self.next_id += len(vectors)
        return ids

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[int], List[float], List[Dict[str, Any]]]:
        if self.next_id == 0:
            return [], [], []

        query_vec = np.ascontiguousarray(query_vector, dtype=np.float32).flatten().tolist()

        q_filter = None
        if metadata_filter:
            must_conditions = [
                rest_models.FieldCondition(key=k, match=rest_models.MatchValue(value=v))
                for k, v in metadata_filter.items()
            ]
            q_filter = rest_models.Filter(must=must_conditions)

        res = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vec,
            query_filter=q_filter,
            limit=k,
        )

        indices: List[int] = []
        distances: List[float] = []
        metadatas: List[Dict[str, Any]] = []

        for p in res.points:
            idx = int(p.id)
            indices.append(idx)
            distances.append(float(p.score))
            metadatas.append(p.payload or self.id_to_metadata.get(idx, {}))

        return indices, distances, metadatas

    def delete_by_filter(self, filters: Dict[str, Any]) -> int:
        to_delete = [
            i for i, m in self.id_to_metadata.items()
            if all(m.get(k) == v for k, v in filters.items())
        ]
        if not to_delete:
            return 0

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=rest_models.PointIdsList(points=to_delete),
        )
        for idx in to_delete:
            del self.id_to_metadata[idx]

        return len(to_delete)
