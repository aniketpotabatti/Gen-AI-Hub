"""Evaluation metrics for predicted vs ground-truth ProductTags (plan Phase 4).

Metrics implemented from the plan's Evaluation Strategy:
  - Exact Match Ratio (all tags equal)
  - Attribute-wise precision / recall / F1 (scalar + list fields)
  - Hierarchical accuracy (credit when prediction matches a ground-truth
    category at parent level; taxonomy parent map is configurable)
  - Latency (mean seconds per product, from pipeline records)
  - Cost (mean USD per product, from CostTracker summary)
"""

from typing import Any, Iterable, Optional

LIST_FIELDS = ("color", "material", "style", "usage_occasion")
SCALAR_FIELDS = (
    "category", "subcategory", "brand", "pattern",
    "gender", "age_group", "size", "is_waterproof",
)
ALL_TAG_FIELDS = SCALAR_FIELDS + LIST_FIELDS

# Child -> parent mapping for hierarchical accuracy (extend via taxonomy).
DEFAULT_TAXONOMY_PARENTS = {
    "sneakers": "footwear",
    "boots": "footwear",
    "t-shirt": "apparel",
    "dress": "apparel",
    "jacket": "apparel",
    "smartphone": "electronics",
    "laptop": "electronics",
    "chair": "home & garden",
    "lamp": "home & garden",
}


def _as_set(value: Any) -> set:
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(v).lower() for v in value}
    if isinstance(value, bool):
        return {value}
    return {str(value).lower()}


def _parent(value: Any, parents: dict) -> Optional[str]:
    if value is None:
        return None
    key = value.lower() if isinstance(value, str) else value
    return parents.get(key)


def attribute_scores(
    predictions: Iterable[dict], ground_truths: Iterable[dict]
) -> dict[str, dict[str, float]]:
    """Precision / recall / F1 per tag attribute (multilabel-style sets)."""
    preds, truths = list(predictions), list(ground_truths)
    if len(preds) != len(truths):
        raise ValueError(
            f"Count mismatch: {len(preds)} predictions vs {len(truths)} ground truths."
        )
    scores: dict[str, dict[str, float]] = {}
    for field_name in ALL_TAG_FIELDS:
        tp = fp = fn = 0
        for pred, truth in zip(preds, truths):
            p, t = _as_set(pred.get(field_name)), _as_set(truth.get(field_name))
            tp += len(p & t)
            fp += len(p - t)
            fn += len(t - p)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        scores[field_name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }
    return scores


def exact_match_ratio(predictions: Iterable[dict], ground_truths: Iterable[dict]) -> float:
    """Fraction of products where every tag field matches exactly."""
    preds, truths = list(predictions), list(ground_truths)
    if not truths:
        return 0.0
    matches = sum(
        all(_as_set(p.get(f)) == _as_set(t.get(f)) for f in ALL_TAG_FIELDS)
        for p, t in zip(preds, truths)
    )
    return round(matches / len(truths), 4)


def hierarchical_accuracy(
    predictions: Iterable[dict],
    ground_truths: Iterable[dict],
    field: str = "subcategory",
    parents: Optional[dict] = None,
) -> float:
    """Accuracy with partial credit at the taxonomy parent level.

    Full credit for an exact match; half credit when the prediction's parent
    equals the truth (or vice versa); else zero.
    """
    parents = parents or DEFAULT_TAXONOMY_PARENTS
    preds, truths = list(predictions), list(ground_truths)
    if not truths:
        return 0.0
    total = 0.0
    for pred, truth in zip(preds, truths):
        p, t = pred.get(field), truth.get(field)
        if p == t or _as_set(p) == _as_set(t):
            total += 1.0
        elif _parent(p, parents) == (t.lower() if isinstance(t, str) else t):
            total += 0.5
        elif (p.lower() if isinstance(p, str) else p) == _parent(t, parents):
            total += 0.5
    return round(total / len(truths), 4)


def latency_stats(records: Iterable[dict]) -> dict[str, float]:
    """Mean / min / max latency from pipeline result records."""
    values = [r.get("latency_s", 0.0) or 0.0 for r in records]
    if not values:
        return {"mean_s": 0.0, "min_s": 0.0, "max_s": 0.0}
    return {
        "mean_s": round(sum(values) / len(values), 4),
        "min_s": round(min(values), 4),
        "max_s": round(max(values), 4),
    }


def evaluate(
    predictions: Iterable[dict],
    ground_truths: Iterable[dict],
    records: Optional[Iterable[dict]] = None,
    cost_summary: Optional[dict] = None,
) -> dict:
    """Compute the full metric report from the plan's evaluation strategy."""
    preds, truths = list(predictions), list(ground_truths)
    report = {
        "n": len(truths),
        "exact_match_ratio": exact_match_ratio(preds, truths),
        "attributes": attribute_scores(preds, truths),
        "hierarchical_accuracy_subcategory": hierarchical_accuracy(preds, truths),
    }
    macro_f1 = sum(a["f1"] for a in report["attributes"].values()) / len(ALL_TAG_FIELDS)
    report["macro_f1"] = round(macro_f1, 4)
    if records is not None:
        report["latency"] = latency_stats(records)
    if cost_summary is not None:
        report["avg_cost_usd_per_product"] = cost_summary.get(
            "avg_cost_usd_per_product", 0.0
        )
        report["total_cost_usd"] = cost_summary.get("total_cost_usd", 0.0)
    return report
