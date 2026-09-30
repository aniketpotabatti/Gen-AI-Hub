"""Adaptive retrieval router: classify query -> select strategies/depth/rerank.

Routing table (plan Phase 4 & 5):
- conceptual  -> dense-heavy hybrid + rerank (semantic retrieval)
- identifier  -> lexical + exact match, no rerank needed (verbatim hit wins)
- comparison  -> multi-query retrieval (decompose into sub-queries, search each arm)
- version     -> version-aware retrieval (dense + BM25 with metadata filter)
- evidence    -> evidence-focused retrieval (deep candidates + rerank)
"""
from typing import Any, Dict, List, Optional

from adaptive_router.classifier import classify
from evaluation.explainability import RetrievalExplainer
from query_intelligence.rewriter import QueryRewriter
from query_intelligence.expander import QueryExpander
from query_intelligence.decomposer import QueryDecomposer
from query_intelligence.hyde import HyDEGenerator
from query_intelligence.entity_extractor import EntityExtractor
from query_intelligence.difficulty import estimate_query_difficulty

# category -> (strategies, candidate_k, rerank, weights, intelligence_actions)
_ROUTES: Dict[str, Dict[str, Any]] = {
    "conceptual": {
        "strategies": ["dense", "bm25"],
        "candidate_k": 20,
        "rerank": True,
        "weights": {"dense": 1.5, "bm25": 1.0, "exact": 0.5},
        "expand": True,
        "hyde": True,
    },
    "identifier": {
        "strategies": ["bm25", "exact", "dense"],
        "candidate_k": 10,
        "rerank": False,
        "weights": {"dense": 0.5, "bm25": 1.5, "exact": 2.0},
        "expand": False,
        "hyde": False,
    },
    "comparison": {
        "strategies": ["dense", "bm25"],
        "candidate_k": 20,
        "rerank": True,
        "weights": {"dense": 1.0, "bm25": 1.0, "exact": 0.5},
        "multi_query": True,
        "decompose": True,
        "expand": False,
        "hyde": False,
    },
    "version": {
        "strategies": ["dense", "bm25"],
        "candidate_k": 15,
        "rerank": True,
        "weights": {"dense": 1.0, "bm25": 1.5, "exact": 1.0},
        "expand": True,
        "hyde": False,
    },
    "evidence": {
        "strategies": ["dense", "bm25", "exact"],
        "candidate_k": 30,
        "rerank": True,
        "weights": {"dense": 1.0, "bm25": 1.0, "exact": 1.0},
        "expand": True,
        "hyde": False,
    },
}


def route(query: str) -> Dict[str, Any]:
    """Return routing decision {category, confidence, signals, ...params}."""
    cls = classify(query)
    params = _ROUTES.get(cls["category"], _ROUTES["conceptual"])
    return {**cls, **params}


def _split_comparison(query: str) -> List[str]:
    """Split 'X vs Y' style queries into per-arm sub-queries."""
    import re

    parts = re.split(r"\bvs\.?\b|\bversus\b|\bcompared to\b|\bcompare\b",
                     query, flags=re.IGNORECASE)
    arms = [p.strip(" ?.,") for p in parts if p.strip(" ?.,")]
    return arms if len(arms) >= 2 else [query]


class AdaptiveRetriever:
    """Wraps HybridRetriever with query intelligence and per-query routing decisions."""

    def __init__(self, hybrid):
        self.hybrid = hybrid
        self.rewriter = QueryRewriter()
        self.expander = QueryExpander()
        self.decomposer = QueryDecomposer()
        self.hyde = HyDEGenerator()
        self.entity_extractor = EntityExtractor()
        self.explainer = RetrievalExplainer()

    def search(
        self,
        query: str,
        k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        enable_intelligence: bool = True,
        explain: bool = False,
    ) -> Dict[str, Any]:
        """Route the query with optional query intelligence, run retrieval, return {route, results, intelligence}."""
        processed_query = query
        search_query = query
        applied_transformations = []
        extracted_entities = {}
        difficulty_info = {}

        if enable_intelligence:
            if conversation_history:
                processed_query = self.rewriter.rewrite_with_history(query, conversation_history)
                if processed_query != query:
                    applied_transformations.append("history_rewrite")
            else:
                processed_query = self.rewriter.normalize(query)
                if processed_query != query:
                    applied_transformations.append("normalization")

            extracted_entities = self.entity_extractor.extract(processed_query)
            difficulty_info = estimate_query_difficulty(processed_query)
            search_query = processed_query

        decision = route(processed_query)
        strategies = list(decision["strategies"])
        candidate_k = decision["candidate_k"]
        rerank = decision["rerank"]

        if enable_intelligence:
            if decision.get("expand") and difficulty_info.get("score", 0.0) >= 0.4:
                expanded = self.expander.expand(search_query)
                if expanded != search_query:
                    search_query = expanded
                    applied_transformations.append("expansion")

            if decision.get("hyde") and difficulty_info.get("level") == "hard":
                hypo_doc = self.hyde.generate(processed_query)
                if hypo_doc:
                    search_query = f"{search_query} {hypo_doc}"
                    applied_transformations.append("hyde")

        old_weights = self.hybrid.weights
        self.hybrid.weights = decision["weights"]
        try:
            # Multi-query fanout for comparative / compound decomposed questions
            decomposed_arms = self.decomposer.decompose(processed_query)
            if decision.get("multi_query") or (enable_intelligence and len(decomposed_arms) > 1):
                results = self._multi_query_search(
                    processed_query, k, candidate_k, metadata_filter, strategies, rerank)
            else:
                results = self.hybrid.search(
                    search_query, k=k, candidate_k=candidate_k,
                    metadata_filter=metadata_filter,
                    strategies=strategies, rerank=rerank)
        finally:
            self.hybrid.weights = old_weights

        for r in results:
            r["route"] = decision["category"]

        out = {"route": decision, "results": results}
        if enable_intelligence:
            out["intelligence"] = {
                "original_query": query,
                "processed_query": processed_query,
                "transformed_query": search_query,
                "transformations": applied_transformations,
                "entities": extracted_entities,
                "difficulty": difficulty_info,
            }
        if explain:
            out["explanations"] = self.explainer.explain_batch(
                query=query,
                results=results,
                text_lookup_fn=lambda cid, m: self.hybrid._full_text(cid, m),
            )
        return out

    def _multi_query_search(self, query: str, k: int, candidate_k: int,
                            metadata_filter, strategies, rerank) -> List[Dict]:
        """Search each comparison arm, interleave by RRF score."""
        arms = _split_comparison(query)
        seen: Dict[str, Dict] = {}
        for arm in arms:
            for r in self.hybrid.search(
                    arm, k=k, candidate_k=candidate_k,
                    metadata_filter=metadata_filter,
                    strategies=strategies, rerank=False):
                if r["chunk_id"] not in seen or r["rrf_score"] > seen[r["chunk_id"]]["rrf_score"]:
                    seen[r["chunk_id"]] = r
        pooled = sorted(seen.values(), key=lambda r: r["rrf_score"], reverse=True)
        if rerank and self.hybrid.reranker is not None and pooled:
            from reranking.normalize import minmax

            cands = pooled[:candidate_k]
            texts = [self.hybrid._full_text(r["chunk_id"], r["metadata"]) for r in cands]
            raw = self.hybrid.reranker.score(query, texts)
            normed = minmax([float(s) for s in raw])
            for r, s, n in zip(cands, raw, normed):
                r["reranker_score"] = float(s)
                r["reranker_norm"] = float(n)
                if "rerank" not in r["strategies"]:
                    r["strategies"] = r["strategies"] + ["rerank"]
            pooled = sorted(cands, key=lambda r: r["reranker_norm"], reverse=True) + pooled[len(cands):]
        return pooled[:k]
