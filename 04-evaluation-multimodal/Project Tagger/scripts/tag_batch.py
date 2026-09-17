"""CLI: batch tag products from CSV/JSONL input -> JSONL output."""

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli_common import (  # noqa: E402
    add_common_args,
    build_pipeline,
    logger,
    print_cost_summary,
    product_from_row,
)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch tag products from CSV/JSONL into JSONL results."
    )
    parser.add_argument("--input", required=True, help="Input CSV or JSONL file.")
    parser.add_argument("--output", required=True, help="Output JSONL file.")
    add_common_args(parser)
    return parser.parse_args(argv)


def load_products(input_path: Path) -> list:
    """Load ProductInput rows from CSV or JSONL."""
    input_path = Path(input_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    suffix = input_path.suffix.lower()
    if suffix == ".jsonl":
        with input_path.open(encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
    elif suffix == ".csv":
        with input_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    else:
        raise ValueError(f"Unsupported input format '{suffix}'. Use .csv or .jsonl.")
    return [product_from_row(row, default_dir=input_path.parent) for row in rows]


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))
    products = load_products(Path(args.input))
    logger.info("Loaded %d products from %s", len(products), args.input)
    pipeline = build_pipeline(args)
    results = pipeline.tag_batch_sync(products, Path(args.output))
    succeeded = sum(1 for r in results if r["error"] is None)
    logger.info(
        "Tagged %d/%d products -> %s", succeeded, len(results), args.output
    )
    print_cost_summary(pipeline)
    return 0 if succeeded == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
