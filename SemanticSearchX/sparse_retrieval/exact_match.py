"""Exact-match retrieval: finds chunks containing the verbatim query string."""
from typing import Any, Dict, List, Optional, Tuple

from utils.helpers import matches_metadata


class ExactMatchIndex:
    def __init__(self, case_sensitive: bool = False):
        self.case_sensitive = case_sensitive
        self.texts: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []

    def __len__(self) -> int:
        return len(self.texts)

    def add_documents(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None):
        if metadatas is not None and len(metadatas) != len(texts):
            raise ValueError("metadatas length must match texts length")
        for i, text in enumerate(texts):
            self.texts.append(text)
            self.metadatas.append(dict(metadatas[i]) if metadatas else {})

    @staticmethod
    def _matches(meta: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        return matches_metadata(meta, filters)

    def search(
        self,
        query: str,
        k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[int], List[float], List[Dict[str, Any]]]:
        if not self.texts or not query or not query.strip():
            return [], [], []
        needle = query.strip()
        if not self.case_sensitive:
            needle = needle.lower()
        indices, dists, metas = [], [], []
        for i, text in enumerate(self.texts):
            hay = text if self.case_sensitive else text.lower()
            if needle in hay:
                if not self._matches(self.metadatas[i], metadata_filter):
                    continue
                # Score: longer query relative to chunk => stronger match.
                score = len(needle) / max(len(hay), 1)
                indices.append(i)
                dists.append(score)
                metas.append(self.metadatas[i])
                if len(indices) == k:
                    break
        return indices, dists, metas

    def delete_by_filter(self, filters: Dict[str, Any]) -> int:
        keep = [(t, m) for t, m in zip(self.texts, self.metadatas)
                if not self._matches(m, filters)]
        removed = len(self.texts) - len(keep)
        if removed:
            self.texts = [t for t, _ in keep]
            self.metadatas = [m for _, m in keep]
        return removed
