"""Retrieval evaluation metrics:
- Quality: Recall@K, Precision@K, MRR, nDCG@K, Hit Rate@K, Context Precision@K, Context Recall@K
- Binary and graded relevance support
"""
import math
from typing import Dict, List, Set, Union


def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Proportion of relevant documents retrieved in top-k."""
    if not relevant:
        return 0.0
    return len(set(retrieved[:k]) & relevant) / len(relevant)


def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Proportion of top-k retrieved documents that are relevant."""
    if k <= 0:
        return 0.0
    top = retrieved[:k]
    if not top:
        return 0.0
    return len(set(top) & relevant) / k


def hit_rate_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """1.0 if at least one relevant document is in top-k, else 0.0."""
    if not relevant:
        return 0.0
    return 1.0 if set(retrieved[:k]) & relevant else 0.0


def mrr(retrieved: List[str], relevant: Set[str]) -> float:
    """Mean Reciprocal Rank: 1 / rank of first relevant item, or 0.0."""
    for rank, cid in enumerate(retrieved, start=1):
        if cid in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain at rank k (binary relevance)."""
    dcg = sum(1.0 / math.log2(rank + 1) for rank, cid in enumerate(retrieved[:k], start=1)
              if cid in relevant)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def context_precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Mean of precision@r across all ranks r where a relevant item appears in top-k.

    Emphasizes ranking relevant chunks higher up in the context window.
    """
    if not relevant or k <= 0:
        return 0.0
    top = retrieved[:k]
    cum_hits = 0
    precisions = []
    for rank, cid in enumerate(top, start=1):
        if cid in relevant:
            cum_hits += 1
            precisions.append(cum_hits / rank)
    if not precisions:
        return 0.0
    return sum(precisions) / min(len(relevant), k)


def context_recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Alias/grounding of recall@k representing context window coverage."""
    return recall_at_k(retrieved, relevant, k)


def evaluate(
    rankings: Dict[str, List[str]],
    relevance: Dict[str, Set[str]],
    ks: List[int] = (1, 3, 5),
) -> Dict[str, float]:
    """Compute aggregate quality metrics over a test query corpus."""
    out: Dict[str, float] = {}
    n = max(len(relevance), 1)
    for k in ks:
        out[f"recall@{k}"] = sum(
            recall_at_k(rankings.get(q, []), rel, k) for q, rel in relevance.items()
        ) / n
        out[f"precision@{k}"] = sum(
            precision_at_k(rankings.get(q, []), rel, k) for q, rel in relevance.items()
        ) / n
        out[f"hit_rate@{k}"] = sum(
            hit_rate_at_k(rankings.get(q, []), rel, k) for q, rel in relevance.items()
        ) / n
        out[f"ndcg@{k}"] = sum(
            ndcg_at_k(rankings.get(q, []), rel, k) for q, rel in relevance.items()
        ) / n
        out[f"context_precision@{k}"] = sum(
            context_precision_at_k(rankings.get(q, []), rel, k) for q, rel in relevance.items()
        ) / n
        out[f"context_recall@{k}"] = sum(
            context_recall_at_k(rankings.get(q, []), rel, k) for q, rel in relevance.items()
        ) / n

    out["mrr"] = sum(
        mrr(rankings.get(q, []), rel) for q, rel in relevance.items()
    ) / n
    return out

