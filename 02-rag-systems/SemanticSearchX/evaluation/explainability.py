"""Explainability module for SemanticSearchX.

Constructs comprehensive, structured explanations for retrieved documents:
- Final score
- Dense score
- Sparse score (BM25 + Exact)
- Reranker score (raw + normalized)
- Retrieval strategy list
- Matching signals (lexical token overlap, exact entity matches, high semantic similarity)
- Source document & chunk metadata
"""
from typing import Any, Dict, List, Optional
from query_intelligence.entity_extractor import EntityExtractor


class RetrievalExplainer:
    """Generates transparent, structured explanations for retrieved search candidates."""

    def __init__(self):
        self.entity_extractor = EntityExtractor()

    def explain_result(
        self,
        query: str,
        result: Dict[str, Any],
        full_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Produce an explainability dictionary for an individual retrieved item."""
        meta = result.get("metadata", {})
        source_doc = meta.get("source") or meta.get("file_name") or "unknown"
        text = full_text or meta.get("content") or ""

        # Extract matching signals
        signals: List[Dict[str, Any]] = []

        # 1. Lexical / Exact matches
        q_entities = self.entity_extractor.extract(query)
        extracted_codes = q_entities.get("codes", [])
        extracted_quotes = q_entities.get("quotes", [])

        for code in extracted_codes:
            if code in text:
                signals.append({
                    "type": "exact_code_match",
                    "term": code,
                    "confidence": 1.0,
                    "description": f"Exact identifier '{code}' matched in chunk text.",
                })

        for quote in extracted_quotes:
            if quote.lower() in text.lower():
                signals.append({
                    "type": "exact_quote_match",
                    "term": quote,
                    "confidence": 1.0,
                    "description": f"Exact phrase '{quote}' matched in chunk text.",
                })

        # Token overlap matching
        q_tokens = set(query.lower().replace("?", " ").replace("!", " ").replace(".", " ").split())
        doc_tokens = set(text.lower().replace("?", " ").replace("!", " ").replace(".", " ").split())
        overlap = sorted(list(q_tokens & doc_tokens))
        if overlap:
            signals.append({
                "type": "term_overlap",
                "matched_terms": overlap,
                "overlap_count": len(overlap),
                "description": f"Matched {len(overlap)} terms from query: {', '.join(overlap[:5])}",
            })

        # 2. Dense semantic signal
        dense_score = result.get("dense_score", 0.0)
        if dense_score > 0.0:
            signals.append({
                "type": "semantic_similarity",
                "score": round(dense_score, 4),
                "description": f"Bi-encoder semantic similarity of {dense_score:.3f}",
            })

        # 3. Reranker signal
        reranker_score = result.get("reranker_score", 0.0)
        reranker_norm = result.get("reranker_norm", 0.0)
        if "rerank" in result.get("strategies", []):
            signals.append({
                "type": "cross_encoder_rerank",
                "raw_score": round(reranker_score, 4),
                "norm_score": round(reranker_norm, 4),
                "description": f"Cross-encoder relevance scored at {reranker_norm:.3f} normalized",
            })

        # Determine final composite score
        # If reranker was applied, reranker_norm is the primary sorting key, else rrf_score
        final_score = reranker_norm if "rerank" in result.get("strategies", []) else result.get("rrf_score", 0.0)

        sparse_breakdown = {
            "bm25_score": result.get("bm25_score", 0.0),
            "exact_score": result.get("exact_score", 0.0),
            "combined_sparse_score": result.get("bm25_score", 0.0) + result.get("exact_score", 0.0),
        }

        # Build clear, human-readable summary narrative
        strat_names = "+".join(result.get("strategies", [])) or "unknown"
        narrative = (
            f"Chunk '{result.get('chunk_id')}' retrieved via [{strat_names}] with final score {final_score:.4f}. "
            f"Source document: '{source_doc}'. "
        )
        if extracted_codes and any(s["type"] == "exact_code_match" for s in signals):
            narrative += f"Triggered high-priority exact identifier match on {extracted_codes}. "
        elif dense_score > 0.5:
            narrative += f"Exhibits strong semantic alignment ({dense_score:.2f}). "

        return {
            "chunk_id": result.get("chunk_id"),
            "final_score": round(final_score, 4),
            "dense_score": round(dense_score, 4),
            "sparse_score": sparse_breakdown,
            "reranker_score": {
                "raw": round(reranker_score, 4),
                "normalized": round(reranker_norm, 4),
            },
            "retrieval_strategy": result.get("strategies", []),
            "route": result.get("route", "default"),
            "matching_signals": signals,
            "source_document": source_doc,
            "chunk_metadata": meta,
            "narrative": narrative.strip(),
        }

    def explain_batch(
        self,
        query: str,
        results: List[Dict[str, Any]],
        text_lookup_fn: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Explain a ranked list of results."""
        explanations = []
        for r in results:
            cid = r.get("chunk_id", "")
            meta = r.get("metadata", {})
            full_text = text_lookup_fn(cid, meta) if text_lookup_fn else meta.get("content", "")
            exp = self.explain_result(query, r, full_text=full_text)
            explanations.append(exp)
        return explanations
