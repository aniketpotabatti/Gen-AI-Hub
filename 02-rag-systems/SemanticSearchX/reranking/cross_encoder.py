from typing import List, Tuple

from utils.helpers import tokenize


class Reranker:
    """Cross-encoder reranker with an offline-safe token-overlap fallback.

    Uses a sentence-transformers CrossEncoder when importable AND loadable,
    otherwise falls back to a deterministic Jaccard-style token scorer so the
    pipeline, demos, and tests run without network access or model weights.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)
        except Exception as e:
            print(f"Warning: using heuristic reranker fallback ({e})")
            self.model = None

    @property
    def uses_cross_encoder(self) -> bool:
        return self.model is not None

    @staticmethod
    def _heuristic_scores(query: str, texts: List[str]) -> List[float]:
        qtoks = set(tokenize(query))
        out = []
        for t in texts:
            ttoks = set(tokenize(t))
            if not qtoks or not ttoks:
                out.append(0.0)
                continue
            inter = len(qtoks & ttoks)
            # F1-ish overlap between query and chunk token sets.
            p = inter / len(ttoks)
            r = inter / len(qtoks)
            out.append(2 * p * r / (p + r) if (p + r) else 0.0)
        return out

    def score(self, query: str, texts: List[str]) -> List[float]:
        if not texts:
            return []
        if self.model is not None:
            try:
                pairs = [(query, t) for t in texts]
                return [float(s) for s in self.model.predict(pairs)]
            except Exception as e:
                print(f"Warning: cross-encoder predict failed ({e}); using heuristic.")
                self.model = None
        return self._heuristic_scores(query, texts)

    def rerank(self, query: str, texts: List[str], top_k: int = 5) -> Tuple[List[int], List[float]]:
        """Return (order, scores): indices into texts sorted best-first, capped at top_k."""
        scores = self.score(query, texts)
        order = sorted(range(len(texts)), key=lambda i: scores[i], reverse=True)[:top_k]
        return order, [scores[i] for i in order]
