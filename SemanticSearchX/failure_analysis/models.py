"""Enum and data structures for Retrieval Failure Analysis."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class FailureCategory(str, Enum):
    """10 Core Retrieval Failure Categories (SemanticSearchX Plan Phase 8)."""
    MISSING_DOCUMENT = "missing_document"
    POOR_CHUNKING = "poor_chunking"
    EMBEDDING_MISMATCH = "embedding_mismatch"
    LEXICAL_MISMATCH = "lexical_mismatch"
    SEMANTIC_MISMATCH = "semantic_mismatch"
    RANKING_FAILURE = "ranking_failure"
    QUERY_INTERPRETATION_FAILURE = "query_interpretation_failure"
    METADATA_FILTER_FAILURE = "metadata_filter_failure"
    MULTI_HOP_FAILURE = "multi_hop_failure"
    OUT_OF_CORPUS_QUERY = "out_of_corpus_query"
    NO_FAILURE = "no_failure"


@dataclass
class FailureDiagnosis:
    """Detailed diagnosis for a query retrieval failure."""
    query: str
    category: FailureCategory
    confidence: float
    reason: str
    candidate_retrieved_ids: List[str] = field(default_factory=list)
    expected_relevant_ids: Set[str] = field(default_factory=set)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    recommended_action: str = ""
