"""Retrieval failure categorizer.

Analyzes query, retrieval response, ground truth relevance, and corpus chunks to
automatically detect and categorize retrieval failures across all 10 plan-specified categories:
1. Missing document
2. Poor chunking
3. Embedding mismatch
4. Lexical mismatch
5. Semantic mismatch
6. Ranking failure
7. Query interpretation failure
8. Metadata-filter failure
9. Multi-hop failure
10. Out-of-corpus query
"""
from typing import Any, Dict, List, Optional, Set

from failure_analysis.models import FailureCategory, FailureDiagnosis
from query_intelligence.entity_extractor import EntityExtractor


class FailureCategorizer:
    """Diagnoses retrieval outcomes and maps failures to root causes."""

    def __init__(self, corpus_chunks: Optional[Dict[str, str]] = None, corpus_metadatas: Optional[Dict[str, Dict[str, Any]]] = None):
        self.corpus_chunks = corpus_chunks or {}
        self.corpus_metadatas = corpus_metadatas or {}
        self.entity_extractor = EntityExtractor()
    def diagnose(
        self,
        query: str,
        retrieved_results: List[Dict[str, Any]],
        expected_relevant_ids: Set[str],
        candidate_pool: Optional[List[Dict[str, Any]]] = None,
        applied_metadata_filter: Optional[Dict[str, Any]] = None,
        route_decision: Optional[Dict[str, Any]] = None,
        sub_query_results: Optional[Dict[str, List[str]]] = None,
        is_known_out_of_corpus: bool = False,
    ) -> FailureDiagnosis:
        """Diagnose a single query retrieval outcome."""
        retrieved_ids = [r.get("chunk_id", "") for r in retrieved_results]
        top_k_hits = set(retrieved_ids) & expected_relevant_ids

        # 9. Multi-hop failure check (when multiple arms are required and any arm fails)
        if sub_query_results and len(sub_query_results) > 1:
            failed_arms = [arm for arm, hits in sub_query_results.items() if not hits]
            if failed_arms:
                return FailureDiagnosis(
                    query=query,
                    category=FailureCategory.MULTI_HOP_FAILURE,
                    confidence=0.85,
                    reason=f"Multi-hop sub-query arm(s) failed to retrieve documents: {failed_arms}",
                    candidate_retrieved_ids=retrieved_ids,
                    expected_relevant_ids=expected_relevant_ids,
                    diagnostics={"failed_arms": failed_arms},
                    recommended_action="Improve sub-query decomposition or use iterative retrieval.",
                )

        # If top-k contains at least one relevant document, no failure occurred!
        if top_k_hits and not is_known_out_of_corpus:
            return FailureDiagnosis(
                query=query,
                category=FailureCategory.NO_FAILURE,
                confidence=1.0,
                reason="Retrieved relevant chunk in top-k successfully.",
                candidate_retrieved_ids=retrieved_ids,
                expected_relevant_ids=expected_relevant_ids,
                recommended_action="No remediation needed.",
            )

        # 10. Out-of-corpus query
        if is_known_out_of_corpus or len(expected_relevant_ids) == 0:
            return FailureDiagnosis(
                query=query,
                category=FailureCategory.OUT_OF_CORPUS_QUERY,
                confidence=0.95,
                reason="Query is unanswerable or requests topics not present in indexed corpus.",
                candidate_retrieved_ids=retrieved_ids,
                expected_relevant_ids=expected_relevant_ids,
                recommended_action="Route to fallback model or state insufficient knowledge.",
            )

        # 1. Missing document
        missing_from_corpus = [cid for cid in expected_relevant_ids if cid not in self.corpus_chunks]
        if len(missing_from_corpus) == len(expected_relevant_ids):
            return FailureDiagnosis(
                query=query,
                category=FailureCategory.MISSING_DOCUMENT,
                confidence=1.0,
                reason=f"Target chunks {missing_from_corpus} were never indexed into the corpus.",
                candidate_retrieved_ids=retrieved_ids,
                expected_relevant_ids=expected_relevant_ids,
                diagnostics={"missing_chunks": missing_from_corpus},
                recommended_action="Ingest and index missing source documents into the vector/sparse store.",
            )

        # 8. Metadata-filter failure
        if applied_metadata_filter:
            filtered_out_relevant = []
            for cid in expected_relevant_ids:
                meta = self.corpus_metadatas.get(cid, {})
                for k, v in applied_metadata_filter.items():
                    if k not in meta or meta[k] != v:
                        filtered_out_relevant.append(cid)
                        break
            if filtered_out_relevant:
                return FailureDiagnosis(
                    query=query,
                    category=FailureCategory.METADATA_FILTER_FAILURE,
                    confidence=0.95,
                    reason=f"Relevant chunk(s) {filtered_out_relevant} excluded by filter {applied_metadata_filter}.",
                    candidate_retrieved_ids=retrieved_ids,
                    expected_relevant_ids=expected_relevant_ids,
                    diagnostics={"filter": applied_metadata_filter, "excluded_chunks": filtered_out_relevant},
                    recommended_action="Relax metadata filters or verify source metadata tagging.",
                )
        # 6. Ranking failure
        if candidate_pool:
            cand_ids = [c.get("chunk_id", "") for c in candidate_pool]
            cand_hits = set(cand_ids) & expected_relevant_ids
            if cand_hits and not top_k_hits:
                return FailureDiagnosis(
                    query=query,
                    category=FailureCategory.RANKING_FAILURE,
                    confidence=0.90,
                    reason=f"Relevant chunk(s) {cand_hits} in candidate pool, but reranker or truncation demoted them outside top-k.",
                    candidate_retrieved_ids=retrieved_ids,
                    expected_relevant_ids=expected_relevant_ids,
                    diagnostics={"candidate_pool_hits": list(cand_hits)},
                    recommended_action="Calibrate reranker scoring thresholds or increase k.",
                )

        # 9. Multi-hop failure
        if sub_query_results and len(sub_query_results) > 1:
            failed_arms = [arm for arm, hits in sub_query_results.items() if not hits]
            if failed_arms:
                return FailureDiagnosis(
                    query=query,
                    category=FailureCategory.MULTI_HOP_FAILURE,
                    confidence=0.85,
                    reason=f"Multi-hop sub-query arm(s) failed to retrieve documents: {failed_arms}",
                    candidate_retrieved_ids=retrieved_ids,
                    expected_relevant_ids=expected_relevant_ids,
                    diagnostics={"failed_arms": failed_arms},
                    recommended_action="Improve sub-query decomposition or use iterative retrieval.",
                )

        # 7. Query interpretation failure
        entities = self.entity_extractor.extract(query)
        if entities.get("codes") and route_decision:
            if "exact" not in route_decision.get("strategies", []) and "bm25" not in route_decision.get("strategies", []):
                return FailureDiagnosis(
                    query=query,
                    category=FailureCategory.QUERY_INTERPRETATION_FAILURE,
                    confidence=0.85,
                    reason=f"Query has exact codes {entities['codes']} but routed to dense-only strategy.",
                    candidate_retrieved_ids=retrieved_ids,
                    expected_relevant_ids=expected_relevant_ids,
                    diagnostics={"entities": entities, "route": route_decision},
                    recommended_action="Adjust routing rules to prioritize exact/BM25 for identifier queries.",
                )

        # 2. Poor chunking
        for cid in expected_relevant_ids:
            chunk_text = self.corpus_chunks.get(cid, "")
            if 0 < len(chunk_text) < 40:
                return FailureDiagnosis(
                    query=query,
                    category=FailureCategory.POOR_CHUNKING,
                    confidence=0.80,
                    reason=f"Relevant chunk {cid} is under-sized ({len(chunk_text)} chars), fragmenting context.",
                    candidate_retrieved_ids=retrieved_ids,
                    expected_relevant_ids=expected_relevant_ids,
                    diagnostics={"chunk_length": len(chunk_text), "chunk_id": cid},
                    recommended_action="Increase chunk size or overlap in chunking configuration.",
                )

        # 4. Lexical mismatch vs 3. Embedding mismatch
        q_tokens = set(query.lower().replace("?", "").replace("!", "").split())
        lexical_overlaps = []
        for cid in expected_relevant_ids:
            ctext = self.corpus_chunks.get(cid, "").lower()
            c_tokens = set(ctext.replace("?", "").replace("!", "").split())
            overlap = q_tokens & c_tokens
            lexical_overlaps.append(len(overlap))

        max_overlap = max(lexical_overlaps) if lexical_overlaps else 0
        if max_overlap <= 1:
            return FailureDiagnosis(
                query=query,
                category=FailureCategory.LEXICAL_MISMATCH,
                confidence=0.80,
                reason="Query vocabulary does not overlap with expected chunk (synonym/paraphrase disconnect).",
                candidate_retrieved_ids=retrieved_ids,
                expected_relevant_ids=expected_relevant_ids,
                diagnostics={"max_token_overlap": max_overlap},
                recommended_action="Enable query expansion or HyDE to bridge lexical vocabulary gaps.",
            )

        if max_overlap >= 3:
            return FailureDiagnosis(
                query=query,
                category=FailureCategory.EMBEDDING_MISMATCH,
                confidence=0.75,
                reason="Query shares significant lexical overlap with target chunk, but dense bi-encoder failed to retrieve it.",
                candidate_retrieved_ids=retrieved_ids,
                expected_relevant_ids=expected_relevant_ids,
                diagnostics={"max_token_overlap": max_overlap},
                recommended_action="Fine-tune embedding model or adjust dense/sparse RRF weights.",
            )

        # 5. Semantic mismatch default
        return FailureDiagnosis(
            query=query,
            category=FailureCategory.SEMANTIC_MISMATCH,
            confidence=0.70,
            reason="Retrieved candidates diverge semantically from intent of query.",
            candidate_retrieved_ids=retrieved_ids,
            expected_relevant_ids=expected_relevant_ids,
            recommended_action="Increase retrieval depth and utilize cross-encoder reranking.",
        )


    def update_corpus(self, chunks: Dict[str, str], metadatas: Optional[Dict[str, Dict[str, Any]]] = None):
        self.corpus_chunks.update(chunks)
        if metadatas:
            self.corpus_metadatas.update(metadatas)
