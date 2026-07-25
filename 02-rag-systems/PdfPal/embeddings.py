import os
from typing import List, Union
import numpy as np
from huggingface_hub import InferenceClient
from langchain_core.embeddings import Embeddings

# Fix OpenMP conflicts on certain platforms
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


class HuggingFaceAPIEmbeddings(Embeddings):
    """Custom LangChain Embeddings wrapper using Hugging Face InferenceClient."""

    def __init__(self, model: str, api_key: Union[str, None] = None):
        self.model = model
        self.api_key = api_key
        self._client: Union[InferenceClient, None] = None

    @property
    def client(self) -> InferenceClient:
        """Lazy initialization of Hugging Face InferenceClient."""
        if self._client is None:
            try:
                token = self.api_key.strip() if (self.api_key and self.api_key.strip()) else None
                self._client = InferenceClient(model=self.model, token=token)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Hugging Face API client: {e}") from e
        return self._client

    @staticmethod
    def _flatten_to_floats(embedding: Union[np.ndarray, List, float, int]) -> List[float]:
        """Convert arbitrary dimensional embedding structure into a flat list of floats."""
        if embedding is None:
            return []
        try:
            arr = np.array(embedding, dtype=np.float32)
            return arr.flatten().tolist()
        except (ValueError, TypeError):
            return []

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of document strings."""
        vectors = []
        for text in texts:
            try:
                embedding = self.client.feature_extraction(text)
                vectors.append(self._flatten_to_floats(embedding))
            except Exception:
                vectors.append([])
        return vectors

    def embed_query(self, text: str) -> List[float]:
        """Embed a single search query string."""
        try:
            embedding = self.client.feature_extraction(text)
            return self._flatten_to_floats(embedding)
        except Exception:
            return []
