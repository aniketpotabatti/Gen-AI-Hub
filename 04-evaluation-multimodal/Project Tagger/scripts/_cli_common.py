"""CLI helpers shared by tag_single.py and tag_batch.py."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline.tagging_pipeline import TaggingPipeline  # noqa: E402
from src.schemas.product import ProductInput  # noqa: E402
from src.tagger.factory import available_providers  # noqa: E402

logger = logging.getLogger("product_tagger")


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Provider / concurrency / few-shot flags shared by both CLIs."""
    parser.add_argument(
        "--provider",
        default=None,
        choices=available_providers(),
        help="VLM provider (default: default_provider in config/models.yaml).",
    )
    parser.add_argument("--model", default=None, help="Override the provider's model.")
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=4,
        help="Max parallel tagging requests (batch mode).",
    )
    parser.add_argument(
        "--few-shot",
        action="store_true",
        help="Append few-shot examples from config/prompts/few_shot_examples.json.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )


def build_pipeline(args: argparse.Namespace) -> TaggingPipeline:
    """Build a TaggingPipeline from parsed CLI args."""
    from src.prompts.loader import load_few_shot_examples
    from src.tagger.factory import create_tagger

    tagger = create_tagger(
        provider=args.provider,
        model=args.model,
        few_shot_examples=load_few_shot_examples() if args.few_shot else None,
    )
    return TaggingPipeline(tagger=tagger, max_concurrency=args.max_concurrency)


def product_from_row(row: dict[str, Any], default_dir: Path | None = None) -> ProductInput:
    """Build a ProductInput from a CSV/JSONL row.

    Accepted keys: product_id (or id), image (or image_path), description.
    Relative image paths resolve against the input file's directory.
    """
    product_id = str(row.get("product_id", row.get("id", "")) or "")
    image_value = row.get("image", row.get("image_path", ""))
    image_path: Path | None = None
    if image_value:
        candidate = Path(str(image_value))
        if not candidate.is_absolute() and default_dir is not None:
            candidate = default_dir / candidate
        image_path = candidate
    return ProductInput(
        product_id=product_id or f"row-{abs(hash(str(row))) % 10**8}",
        image_path=image_path,
        image_base64=row.get("image_base64"),
        description=row.get("description"),
    )


def print_cost_summary(pipeline: TaggingPipeline) -> None:
    """Log the aggregate cost/token summary."""
    summary = pipeline.cost_summary()
    logger.info(
        "Cost summary: %d requests, %d in / %d out tokens, $%.6f total ($%.6f avg/product)",
        summary["requests"],
        summary["total_input_tokens"],
        summary["total_output_tokens"],
        summary["total_cost_usd"],
        summary["avg_cost_usd_per_product"],
    )
