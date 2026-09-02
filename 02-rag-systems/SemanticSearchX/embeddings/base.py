from typing import List, Union
import numpy as np

class EmbeddingModel:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("sentence-transformers is required. Install with `pip install sentence-transformers`")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings

    def get_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()