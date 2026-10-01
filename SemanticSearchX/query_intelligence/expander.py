"""Rule-based query expansion and domain synonym injection."""
from typing import Dict, List, Optional, Set


class QueryExpander:
    """Enriches sparse queries with domain-specific terms and synonyms."""

    DOMAIN_SYNONYMS: Dict[str, List[str]] = {
        "dense": ["vector", "semantic", "embedding", "bi-encoder"],
        "sparse": ["lexical", "bm25", "keyword", "inverted index", "term match"],
        "rerank": ["cross-encoder", "second stage", "reranker", "score reordering"],
        "retrieval": ["search", "lookup", "fetch", "querying"],
        "latency": ["response time", "speed", "throughput", "runtime"],
        "error": ["failure", "exception", "crash", "fault", "bug"],
        "chunking": ["splitting", "segmentation", "sliding window", "partitioning"],
        "fusion": ["rrf", "reciprocal rank fusion", "hybrid combination"],
    }

    def __init__(self, synonym_map: Optional[Dict[str, List[str]]] = None):
        self.synonym_map = synonym_map if synonym_map is not None else self.DOMAIN_SYNONYMS

    def expand(self, query: str, max_additions: int = 3) -> str:
        """Append relevant domain synonyms to a query to assist BM25/lexical matching."""
        if not query:
            return ""
        tokens = query.lower().split()
        added_terms: List[str] = []
        seen: Set[str] = set(tokens)

        for t in tokens:
            cleaned = t.strip("?,.!")
            if cleaned in self.synonym_map:
                for syn in self.synonym_map[cleaned]:
                    if syn.lower() not in seen and syn.lower() not in query.lower():
                        added_terms.append(syn)
                        seen.add(syn.lower())
                        if len(added_terms) >= max_additions:
                            break
            if len(added_terms) >= max_additions:
                break

        if not added_terms:
            return query
        return f"{query} {' '.join(added_terms)}"
