"""Tests for evaluation metrics (exact match, F1, hierarchical, latency, cost)."""

import pytest

from src.evaluation import (
    attribute_scores,
    evaluate,
    exact_match_ratio,
    hierarchical_accuracy,
    latency_stats,
)

TRUTHS = [
    {"category": "apparel", "subcategory": "t-shirt", "color": ["red"], "brand": "Nike"},
    {"category": "footwear", "subcategory": "sneakers", "color": ["black", "white"]},
]


def test_exact_match_ratio():
    assert exact_match_ratio(TRUTHS, TRUTHS) == 1.0
    preds = [dict(TRUTHS[0], color=["blue"]), TRUTHS[1]]
    assert exact_match_ratio(preds, TRUTHS) == 0.5
    assert exact_match_ratio([], []) == 0.0


def test_attribute_scores_perfect_and_partial():
    scores = attribute_scores(TRUTHS, TRUTHS)
    assert scores["category"]["f1"] == 1.0
    preds = [dict(TRUTHS[0], color=["red", "blue"]), TRUTHS[1]]
    scores = attribute_scores(preds, TRUTHS)
    assert scores["color"]["precision"] == 0.75  # 3 tp / (3 tp + 1 fp)
    assert scores["color"]["recall"] == 1.0
    assert scores["color"]["f1"] == pytest.approx(0.8571, abs=1e-4)


def test_attribute_scores_count_mismatch_raises():
    with pytest.raises(ValueError, match="Count mismatch"):
        attribute_scores(TRUTHS[:1], TRUTHS)


def test_hierarchical_accuracy_partial_credit():
    # sneakers -> footwear parent: truth at parent level earns half credit.
    preds = [{"subcategory": "sneakers"}, {"subcategory": "boots"}]
    truths = [{"subcategory": "footwear"}, {"subcategory": "boots"}]
    assert hierarchical_accuracy(preds, truths) == 0.75


def test_latency_stats():
    records = [{"latency_s": 1.0}, {"latency_s": 3.0}]
    assert latency_stats(records) == {"mean_s": 2.0, "min_s": 1.0, "max_s": 3.0}
    assert latency_stats([])["mean_s"] == 0.0


def test_evaluate_full_report():
    report = evaluate(
        TRUTHS,
        TRUTHS,
        records=[{"latency_s": 1.5}],
        cost_summary={"avg_cost_usd_per_product": 0.001, "total_cost_usd": 0.002},
    )
    assert report["n"] == 2
    assert report["exact_match_ratio"] == 1.0
    # Empty fields (None vs None) score 0.0, so macro F1 over all 12 fields is
    # diluted: 4 populated fields at 1.0 -> 4/12 = 0.3333.
    assert report["macro_f1"] == 0.3333
    assert report["hierarchical_accuracy_subcategory"] == 1.0
    assert report["latency"]["mean_s"] == 1.5
    assert report["avg_cost_usd_per_product"] == 0.001


def test_evaluate_macro_f1_only_populated_fields():
    report = evaluate(TRUTHS, TRUTHS)
    assert report["attributes"]["category"]["f1"] == 1.0
    assert report["attributes"]["brand"]["support"] == 1  # only first item has brand
