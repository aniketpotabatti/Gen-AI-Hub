"""Hybrid retrieval: dense + BM25 + exact-match fused with RRF.

Chunk identity is the shared key: dense ids map to chunk_id via
VectorStore metadata, BM25/exact indices carry the same chunk_id
in their metadata. RRF fuses ranked lists without score calibration.
"""
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def reciprocal_rank_fusion(
    ranked_lists: List[List[int]], k: int = 60
) -> Dict[int, float]:
    """Fuse ranked id-lists into {id: rrf_score}. Rank is 1-based."""
    fused: Dict[int, float] = {}
    for lst in ranked_lists:
        for rank, doc_id in enumerate(lst, start=1):
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (k + rank)
    return fused


class HybridRetriever:
    def __init__(self, vector_store, bm25_index, exact_index, embed_model,
                 weights: Optional[Dict[str, float]] = None,
                 rrf_k: int = 60, reranker=None):
        self.vector_store = vector_store
        self.bm25 = bm25_index
        self.exact = exact_index
        self.embed_model = embed_model
        self.weights = weights or {"dense": 1.0, "bm25": 1.0, "exact": 1.0}
        self.rrf_k = rrf_k
        self.reranker = reranker
        # dense position -> chunk_id lookup mirrors VectorStore order.
        self._dense_pos_to_chunk: List[str] = []

    def _dense_chunk_of(self, dense_id: int) -> Optional[str]:
        meta = self.vector_store.id_to_metadata.get(int(dense_id), {})
        return meta.get("chunk_id")

    def index_chunks(self, chunks: List[str], metadatas: List[Dict[str, Any]],
                     embeddings: np.ndarray):
        """Add chunks to all three indices. Skips already-present chunk_ids."""
        if len(chunks) != len(metadatas) or len(chunks) != len(embeddings):
            raise ValueError("chunks, metadatas and embeddings must have the same length")
        existing = {m.get("chunk_id") for m in self.vector_store.id_to_metadata.values()}
        existing |= {m.get("chunk_id") for m in self.bm25.metadatas}
        existing |= {m.get("chunk_id") for m in self.exact.metadatas}
        pairs = [(c, m) for c, m in zip(chunks, metadatas)]
        fresh_idx = [i for i, (_, m) in enumerate(pairs)
                     if m.get("chunk_id") not in existing]
        if not fresh_idx:
            return 0
        fc = [chunks[i] for i in fresh_idx]
        fm = [metadatas[i] for i in fresh_idx]
        fv = np.ascontiguousarray(embeddings[fresh_idx], dtype=np.float32)
        self.vector_store.add_vectors(fv, metadata=fm)
        self.bm25.add_documents(fc, metadatas=fm)
        self.exact.add_documents(fc, metadatas=fm)
        return len(fresh_idx)

    def search(
        self,
        query: str,
        k: int = 5,
        candidate_k: int = 20,
        metadata_filter: Optional[Dict[str, Any]] = None,
        strategies: Optional[List[str]] = None,
        rerank: bool = False,
        reranker=None,
    ) -> List[Dict[str, Any]]:
        """Return fused ranked results with per-strategy score breakdown.

        rerank=True re-scores the top candidate_k fused candidates with the
        configured (or passed) reranker and returns the top k. Adds
        reranker_score + reranker_norm fields for explainability.
        """
        strategies = strategies or ["dense", "bm25", "exact"]
        per_strategy: Dict[str, Tuple[List[Any], List[float], List[Dict]]] = {}

        if "dense" in strategies:
            q_emb = self.embed_model.encode([query])[0]
            d_ids, d_scores, d_metas = self.vector_store.search(
                q_emb, k=candidate_k, metadata_filter=metadata_filter
            )
            per_strategy["dense"] = (d_ids, d_scores, d_metas)
        if "bm25" in strategies:
            b_ids, b_scores, b_metas = self.bm25.search(
                query, k=candidate_k, metadata_filter=metadata_filter
            )
            per_strategy["bm25"] = (b_ids, b_scores, b_metas)
        if "exact" in strategies:
            e_ids, e_scores, e_metas = self.exact.search(
                query, k=candidate_k, metadata_filter=metadata_filter
            )
            per_strategy["exact"] = (e_ids, e_scores, e_metas)

        # Normalize every strategy's hits onto chunk_id keys.
        chunk_rank_lists: Dict[str, List[str]] = {}
        chunk_best: Dict[str, Dict[str, Any]] = {}
        for name, (ids, scores, metas) in per_strategy.items():
            ranked: List[str] = []
            for pos, (i, s, m) in enumerate(zip(ids, scores, metas)):
                if name == "dense":
                    cid = self._dense_chunk_of(i)
                else:
                    cid = m.get("chunk_id")
                if not cid:
                    continue
                ranked.append(cid)
                entry = chunk_best.setdefault(cid, {
                    "chunk_id": cid, "metadata": m,
                    "dense_score": 0.0, "bm25_score": 0.0, "exact_score": 0.0,
                    "strategies": [], "text": "",
                })
                entry[f"{name}_score"] = float(s)
                if name not in entry["strategies"]:
                    entry["strategies"].append(name)
                # Keep richest metadata (prefer dense which has full fields).
                if name == "dense":
                    entry["metadata"] = m
                # Keep full chunk text for the reranker (BM25/exact carry it).
                if name in ("bm25", "exact") and not entry["text"]:
                    entry["text"] = self._full_text(cid, m)
            chunk_rank_lists[name] = ranked

        # Weighted RRF over chunk_id rankings.
        fused: Dict[str, float] = {}
        for name, ranked in chunk_rank_lists.items():
            w = self.weights.get(name, 1.0)
            for rank, cid in enumerate(ranked, start=1):
                fused[cid] = fused.get(cid, 0.0) + w / (self.rrf_k + rank)

        # Rerank stage: re-score top candidate_k fused candidates, keep top k.
        active_reranker = reranker if reranker is not None else self.reranker
        if rerank and active_reranker is not None and fused:
            from reranking.normalize import minmax

            cand_ids = sorted(fused, key=lambda c: fused[c], reverse=True)[:candidate_k]
            texts = [self._full_text(cid, chunk_best[cid]["metadata"])
                     for cid in cand_ids]
            raw = active_reranker.score(query, texts)
            normed = minmax([float(s) for s in raw])
            order = sorted(range(len(cand_ids)),
                           key=lambda i: normed[i], reverse=True)[:k]
            results = []
            for i in order:
                cid = cand_ids[i]
                entry = chunk_best[cid]
                results.append({
                    "chunk_id": cid,
                    "rrf_score": fused[cid],
                    "dense_score": entry["dense_score"],
                    "bm25_score": entry["bm25_score"],
                    "exact_score": entry["exact_score"],
                    "reranker_score": float(raw[i]),
                    "reranker_norm": float(normed[i]),
                    "strategies": entry["strategies"] + ["rerank"],
                    "metadata": entry["metadata"],
                })
            return results

        results = []
        for cid, score in sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:k]:
            entry = chunk_best[cid]
            results.append({
                "chunk_id": cid,
                "rrf_score": score,
                "dense_score": entry["dense_score"],
                "bm25_score": entry["bm25_score"],
                "exact_score": entry["exact_score"],
                "reranker_score": 0.0,
                "reranker_norm": 0.0,
                "strategies": entry["strategies"],
                "metadata": entry["metadata"],
            })
        return results

    def _full_text(self, chunk_id: str, meta: Dict[str, Any]) -> str:
        """Resolve full chunk text: BM25/exact store it, dense meta has preview."""
        for index in (self.bm25, self.exact):
            for t, mm in zip(index.texts, index.metadatas):
                if mm.get("chunk_id") == chunk_id:
                    return t
        return meta.get("content", "")
