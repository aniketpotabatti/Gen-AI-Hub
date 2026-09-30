"""BM25 sparse retrieval over chunk texts.

Uses rank-bm25 when available, otherwise a pure-Python TF-IDF-ish
fallback so tests/demo run without extra deps.
"""
import json
import math
import os
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from utils.helpers import matches_metadata, tokenize


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.texts: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self._tokens: List[List[str]] = []
        self._bm25 = None  # rank_bm25 object when available
        self._doc_freq: Counter = Counter()
        self._avgdl = 0.0

    def __len__(self) -> int:
        return len(self.texts)

    def _rebuild_fallback_stats(self):
        self._doc_freq = Counter()
        total = 0
        for toks in self._tokens:
            total += len(toks)
            for t in set(toks):
                self._doc_freq[t] += 1
        self._avgdl = total / len(self._tokens) if self._tokens else 0.0

    def _try_build_rankbm25(self):
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            self._bm25 = None
            return
        if self._tokens:
            self._bm25 = BM25Okapi(self._tokens, k1=self.k1, b=self.b)
        else:
            self._bm25 = None

    def add_documents(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None):
        if metadatas is not None and len(metadatas) != len(texts):
            raise ValueError("metadatas length must match texts length")
        for i, text in enumerate(texts):
            self.texts.append(text)
            self._tokens.append(tokenize(text))
            self.metadatas.append(dict(metadatas[i]) if metadatas else {})
        self._rebuild_fallback_stats()
        self._try_build_rankbm25()

    @staticmethod
    def _matches(meta: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        return matches_metadata(meta, filters)

    def _fallback_scores(self, query_tokens: List[str]) -> List[float]:
        n = len(self._tokens)
        scores = [0.0] * n
        if n == 0 or not query_tokens:
            return scores
        qtf = Counter(query_tokens)
        for idx, toks in enumerate(self._tokens):
            if not toks:
                continue
            tf = Counter(toks)
            dl = len(toks)
            s = 0.0
            for term in qtf:
                f = tf.get(term, 0)
                if f == 0:
                    continue
                df = self._doc_freq.get(term, 0)
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self._avgdl or 1.0))
                s += idf * (f * (self.k1 + 1) / denom)
            scores[idx] = s
        return scores

    def search(
        self,
        query: str,
        k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[int], List[float], List[Dict[str, Any]]]:
        if not self.texts or not query or not query.strip():
            return [], [], []
        qtoks = tokenize(query)
        if not qtoks:
            return [], [], []
        if self._bm25 is not None:
            scores = [float(s) for s in self._bm25.get_scores(qtoks)]
        else:
            scores = self._fallback_scores(qtoks)
        # rank_bm25 returns all-zero scores on tiny corpora (idf floors at 0
        # when every term appears in a large fraction of docs). Fall back to
        # the pure-Python scorer, whose idf uses log(1 + ...) and stays > 0.
        if all(s <= 0 for s in scores):
            scores = self._fallback_scores(qtoks)
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        indices, dists, metas = [], [], []
        for i in order:
            if scores[i] <= 0:
                continue
            if not self._matches(self.metadatas[i], metadata_filter):
                continue
            indices.append(i)
            dists.append(float(scores[i]))
            metas.append(self.metadatas[i])
            if len(indices) == k:
                break
        return indices, dists, metas

    def delete_by_filter(self, filters: Dict[str, Any]) -> int:
        keep = [(t, m) for t, m in zip(self.texts, self.metadatas) if not self._matches(m, filters)]
        removed = len(self.texts) - len(keep)
        if removed:
            self.texts = [t for t, _ in keep]
            self.metadatas = [m for _, m in keep]
            self._tokens = [tokenize(t) for t in self.texts]
            self._rebuild_fallback_stats()
            self._try_build_rankbm25()
        return removed

    # --- persistence ---
    def save(self, path: str):
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "bm25.json"), "w", encoding="utf-8") as f:
            json.dump(
                {"texts": self.texts, "metadatas": self.metadatas,
                 "k1": self.k1, "b": self.b},
                f,
            )

    def load(self, path: str):
        with open(os.path.join(path, "bm25.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        self.k1 = data.get("k1", 1.5)
        self.b = data.get("b", 0.75)
        self.texts = data.get("texts", [])
        self.metadatas = data.get("metadatas", [])
        self._tokens = [tokenize(t) for t in self.texts]
        self._rebuild_fallback_stats()
        self._try_build_rankbm25()
