"""Robustness evaluation suite for retrieval engines.

Tests retrieval performance against challenging adversarial query types:
- Short queries (underspecified)
- Long verbose queries
- Ambiguous queries
- Typos and misspellings
- Exact identifiers and codes
- Numerical queries
- Temporal queries
- Multi-hop / compound queries
- Multi-turn queries (conversational coreference)
- Out-of-domain queries
- Negative / unanswerable queries
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set

from evaluation.metrics import recall_at_k, precision_at_k, mrr, hit_rate_at_k


@dataclass
class RobustnessTestCase:
    category: str
    query: str
    relevant_chunks: Set[str]
    description: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    is_unanswerable: bool = False


class RobustnessBenchmark:
    """Runs a multi-category robustness benchmark across challenging query distributions."""

    def __init__(self, test_cases: Optional[List[RobustnessTestCase]] = None):
        self.test_cases = test_cases or []

    def add_case(self, case: RobustnessTestCase):
        self.test_cases.append(case)

    def run(
        self,
        retriever_fn: Callable[[str, Optional[List[Dict[str, str]]]], List[str]],
        k: int = 3,
    ) -> Dict[str, Any]:
        """Execute all test cases and compile per-category breakdown and aggregate metrics."""
        category_results: Dict[str, List[Dict[str, float]]] = {}
        unanswerable_tested = 0
        unanswerable_empty_or_low_score = 0

        for case in self.test_cases:
            retrieved = retriever_fn(case.query, case.conversation_history)
            top_k = retrieved[:k]

            if case.is_unanswerable:
                unanswerable_tested += 1
                # Negative queries should ideally yield no relevant chunks
                if not set(top_k) & case.relevant_chunks:
                    unanswerable_empty_or_low_score += 1
                rec = 0.0
                prec = 0.0
                hr = 0.0
                rr = 0.0
            else:
                rec = recall_at_k(top_k, case.relevant_chunks, k)
                prec = precision_at_k(top_k, case.relevant_chunks, k)
                hr = hit_rate_at_k(top_k, case.relevant_chunks, k)
                rr = mrr(top_k, case.relevant_chunks)

            cat = case.category
            if cat not in category_results:
                category_results[cat] = []
            category_results[cat].append({
                "recall": rec,
                "precision": prec,
                "hit_rate": hr,
                "mrr": rr,
            })

        # Summarize by category
        summary_by_cat: Dict[str, Dict[str, float]] = {}
        for cat, scores in category_results.items():
            cnt = len(scores)
            summary_by_cat[cat] = {
                "count": cnt,
                "avg_recall": round(sum(s["recall"] for s in scores) / cnt, 3),
                "avg_precision": round(sum(s["precision"] for s in scores) / cnt, 3),
                "avg_hit_rate": round(sum(s["hit_rate"] for s in scores) / cnt, 3),
                "avg_mrr": round(sum(s["mrr"] for s in scores) / cnt, 3),
            }

        all_valid = [
            s for cat, scores in category_results.items()
            if cat != "negative_unanswerable"
            for s in scores
        ]
        total_valid = max(1, len(all_valid))

        return {
            "total_cases": len(self.test_cases),
            "categories": summary_by_cat,
            "overall_valid_mrr": round(sum(s["mrr"] for s in all_valid) / total_valid, 3),
            "overall_valid_recall": round(sum(s["recall"] for s in all_valid) / total_valid, 3),
            "unanswerable_handling_rate": round(
                unanswerable_empty_or_low_score / max(1, unanswerable_tested), 3
            ) if unanswerable_tested > 0 else 1.0,
        }
