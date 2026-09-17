"""CLI: evaluate predicted tags against ground truth (accuracy, consistency)."""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.evaluation import evaluate  # noqa: E402
from src.pipeline.tagging_pipeline import load_jsonl  # noqa: E402

logger = logging.getLogger("product_tagger")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate predicted tags vs ground truth JSONL."
    )
    parser.add_argument(
        "--predictions", required=True, help="JSONL with predicted records."
    )
    parser.add_argument(
        "--ground-truth", required=True, help="JSONL with ground-truth records."
    )
    parser.add_argument(
        "--output", default=None, help="Optional path to write the JSON report."
    )
    parser.add_argument(
        "--pred-key",
        default="tags",
        help="Record key holding predicted tags (default: 'tags').",
    )
    parser.add_argument(
        "--truth-key",
        default="tags",
        help="Record key holding ground-truth tags (default: 'tags').",
    )
    return parser.parse_args(argv)


def _align(predictions: list[dict], truths: list[dict]) -> tuple[list, list]:
    """Align by product_id when present, else pair by order."""
    truth_by_id = {r.get("product_id"): r for r in truths}
    pred_by_id = {r.get("product_id"): r for r in predictions}
    if truth_by_id and pred_by_id and set(pred_by_id) & set(truth_by_id):
        common = [pid for pid in pred_by_id if pid in truth_by_id]
        return [pred_by_id[pid] for pid in common], [truth_by_id[pid] for pid in common]
    n = min(len(predictions), len(truths))
    if len(predictions) != len(truths):
        logger.warning(
            "No product_id overlap; pairing first %d records by order.", n
        )
    return predictions[:n], truths[:n]


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    pred_records = load_jsonl(Path(args.predictions))
    truth_records = load_jsonl(Path(args.ground_truth))
    preds, truths = _align(pred_records, truth_records)
    predictions = [r.get(args.pred_key, {}) or {} for r in preds]
    ground_truths = [r.get(args.truth_key, {}) or {} for r in truths]
    report = evaluate(predictions, ground_truths, records=pred_records)
    print(json.dumps(report, indent=2))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info("Report written to %s", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
