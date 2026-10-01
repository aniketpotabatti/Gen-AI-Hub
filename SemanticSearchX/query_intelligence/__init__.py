"""Query Intelligence package for SemanticSearchX.

Provides modular query transformations:
- query rewriting (cleaning, canonicalization, typo tolerance)
- query expansion (synonym injection, domain terms)
- query decomposition (multi-part questions into sub-queries)
- multi-query generation (alternative phrasing variations)
- HyDE (hypothetical document embeddings generator)
- entity extraction (identifiers, error codes, domain keywords)
- query difficulty estimation (heuristic ambiguity/specificity score)
- conversation-aware rewriting (resolving coreferences with chat history)
"""
from query_intelligence.rewriter import QueryRewriter
from query_intelligence.expander import QueryExpander
from query_intelligence.decomposer import QueryDecomposer
from query_intelligence.hyde import HyDEGenerator
from query_intelligence.entity_extractor import EntityExtractor
from query_intelligence.difficulty import estimate_query_difficulty

__all__ = [
    "QueryRewriter",
    "QueryExpander",
    "QueryDecomposer",
    "HyDEGenerator",
    "EntityExtractor",
    "estimate_query_difficulty",
]
