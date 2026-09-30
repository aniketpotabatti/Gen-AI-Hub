"""Score normalization helpers for fusing heterogeneous retrieval scores."""
from typing import List


def minmax(scores: List[float]) -> List[float]:
    """Scale scores to [0, 1]. Constant/empty input maps to zeros."""
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi <= lo:
        return [0.0] * len(scores)
    span = hi - lo
    return [(s - lo) / span for s in scores]


def zscore(scores: List[float]) -> List[float]:
    """Standardize to mean 0 / std 1. Constant/empty input maps to zeros."""
    if not scores:
        return []
    mean = sum(scores) / len(scores)
    var = sum((s - mean) ** 2 for s in scores) / len(scores)
    std = var ** 0.5
    if std == 0:
        return [0.0] * len(scores)
    return [(s - mean) / std for s in scores]
