"""Benchmark reporting and diagnostics generation for retrieval failures."""
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, List, Optional, Set

from failure_analysis.categorizer import FailureCategorizer
from failure_analysis.models import FailureCategory, FailureDiagnosis


class FailureBenchmarkReporter:
    """Runs retrieval benchmarks, collects failure diagnoses, and produces summary reports."""

    def __init__(self, categorizer: FailureCategorizer):
        self.categorizer = categorizer

    def analyze_evaluation_run(
        self,
        test_queries: List[Dict[str, Any]],
        retriever_fn: Callable[[str, Optional[Dict[str, Any]]], Dict[str, Any]],
        k: int = 3,
    ) -> Dict[str, Any]:
        """
        Runs failure analysis across a list of query test specifications:
        Each item in test_queries:
          - "query": str
          - "expected_relevant_ids": Set[str]
          - "metadata_filter": Optional[dict]
          - "is_out_of_corpus": Optional[bool]
        """
        diagnoses: List[FailureDiagnosis] = []
        failure_counts: Counter = Counter()
        category_breakdown: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        total_queries = len(test_queries)

        for item in test_queries:
            q = item["query"]
            rel_ids = set(item.get("expected_relevant_ids", set()))
            meta_filter = item.get("metadata_filter")
            is_ooc = item.get("is_out_of_corpus", False)

            # Execute retrieval
            res = retriever_fn(q, meta_filter)
            retrieved_results = res.get("results", [])
            route_decision = res.get("route")
            candidate_pool = res.get("candidate_pool")
            sub_query_results = res.get("sub_query_results")

            diagnosis = self.categorizer.diagnose(
                query=q,
                retrieved_results=retrieved_results,
                expected_relevant_ids=rel_ids,
                candidate_pool=candidate_pool,
                applied_metadata_filter=meta_filter,
                route_decision=route_decision,
                sub_query_results=sub_query_results,
                is_known_out_of_corpus=is_ooc,
            )

            diagnoses.append(diagnosis)
            failure_counts[diagnosis.category.value] += 1
            category_breakdown[diagnosis.category.value].append({
                "query": q,
                "confidence": diagnosis.confidence,
                "reason": diagnosis.reason,
                "recommended_action": diagnosis.recommended_action,
                "diagnostics": diagnosis.diagnostics,
            })

        success_count = failure_counts.get(FailureCategory.NO_FAILURE.value, 0)
        failure_total = total_queries - success_count
        failure_rate = (failure_total / total_queries) if total_queries > 0 else 0.0

        # Build recommendations summary
        top_failure_causes = [
            {"category": cat, "count": count, "percentage": round(count / total_queries * 100, 1)}
            for cat, count in failure_counts.most_common()
            if cat != FailureCategory.NO_FAILURE.value
        ]

        report = {
            "summary": {
                "total_queries": total_queries,
                "successful_retrievals": success_count,
                "failed_retrievals": failure_total,
                "failure_rate": round(failure_rate, 4),
            },
            "failure_counts": dict(failure_counts),
            "top_failure_causes": top_failure_causes,
            "category_breakdown": dict(category_breakdown),
            "diagnoses": diagnoses,
        }
        return report

    def print_report(self, report: Dict[str, Any]):
        """Format and print an executive terminal report."""
        summary = report["summary"]
        print("\n" + "=" * 65)
        print("RETRIEVAL FAILURE ANALYSIS & DIAGNOSTICS REPORT")
        print("=" * 65)
        print(f"Total Queries Evaluated  : {summary['total_queries']}")
        print(f"Successful Retrievals    : {summary['successful_retrievals']}")
        print(f"Failed Retrievals        : {summary['failed_retrievals']}")
        print(f"Overall Failure Rate     : {summary['failure_rate'] * 100:.1f}%\n")

        print("--- Failure Counts by Category ---")
        print(f"{'Category':<32} | {'Count':<6} | {'% of Queries':<12}")
        print("-" * 55)
        for item in report.get("top_failure_causes", []):
            print(f"{item['category']:<32} | {item['count']:<6} | {item['percentage']:<12.1f}%")

        if not report.get("top_failure_causes"):
            print("No failures recorded! All queries satisfied successfully.")

        print("\n--- Diagnostic Findings & Recommendations ---")
        for cat, items in report.get("category_breakdown", {}).items():
            if cat == FailureCategory.NO_FAILURE.value:
                continue
            sample = items[0]
            print(f"\n[Category: {cat.upper()}] (Total: {len(items)})")
            print(f"  Example Query      : \"{sample['query']}\"")
            print(f"  Likely Root Cause  : {sample['reason']}")
            print(f"  Recommended Action : {sample['recommended_action']}")
        print("\n" + "=" * 65)
