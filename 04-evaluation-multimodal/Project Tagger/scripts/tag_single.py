"""CLI: tag a single product (image path + description -> tags as JSON)."""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli_common import (  # noqa: E402
    add_common_args,
    build_pipeline,
    print_cost_summary,
)

from src.schemas.product import ProductInput  # noqa: E402


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tag a single product image + description with a VLM."
    )
    parser.add_argument("--image", required=True, help="Path to the product image.")
    parser.add_argument("--description", default="", help="Product description text.")
    parser.add_argument("--product-id", default="product-001", help="Product identifier.")
    add_common_args(parser)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))
    pipeline = build_pipeline(args)
    product = ProductInput(
        product_id=args.product_id,
        image_path=Path(args.image),
        description=args.description,
    )
    record = pipeline.tag_one(product)
    print(json.dumps(record, indent=2, default=str))
    print_cost_summary(pipeline)
    return 0 if record["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
