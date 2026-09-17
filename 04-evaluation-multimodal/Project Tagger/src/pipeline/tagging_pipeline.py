"""Main pipeline: load -> tag -> validate -> save (plan Phase 3).

`TaggingPipeline.tag_one()` handles a single product synchronously;
`tag_batch()` fans out over a thread pool with a semaphore-style
`max_concurrency` cap (provider SDKs are sync/blocking, so threads — not
asyncio — are the right concurrency primitive here). Results persist as
JSONL: one record per product with tags or error details.
"""

import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, Optional

from src.schemas.product import ProductInput
from src.schemas.tags import ProductTags
from src.tagger.base import BaseTagger, TaggingError
from src.tagger.factory import create_tagger
from src.utils.cost_tracker import CostTracker
from src.validation.validator import validate_tags

logger = logging.getLogger(__name__)


class TaggingPipeline:
    """Orchestrates tagging with validation, batching, and JSONL persistence."""

    def __init__(
        self,
        tagger: Optional[BaseTagger] = None,
        provider: Optional[str] = None,
        cost_tracker: Optional[CostTracker] = None,
        max_concurrency: int = 4,
    ) -> None:
        self.cost_tracker = cost_tracker or CostTracker()
        self.tagger = tagger or create_tagger(
            provider=provider, cost_tracker=self.cost_tracker
        )
        # Keep the tagger's tracker in sync when a prebuilt tagger was passed.
        self.tagger.cost_tracker = self.cost_tracker
        self.max_concurrency = max_concurrency

    # ------------------------------------------------------------------ #
    # Single-product flow
    # ------------------------------------------------------------------ #
    def tag_one(self, product: ProductInput) -> dict:
        """Tag one product; always returns a result record (never raises).

        Record shape: `{"product_id", "tags" | None, "error" | None,
        "usage", "latency_s"}`.
        """
        start = time.perf_counter()
        try:
            tags: ProductTags = self.tagger.tag_product(product)
            result = validate_tags(tags.model_dump())
            record = {
                "product_id": product.product_id,
                "tags": result.tags.model_dump() if result.tags else None,
                "error": None,
                "usage": dict(self.tagger.last_usage),
                "latency_s": round(time.perf_counter() - start, 3),
            }
        except (TaggingError, FileNotFoundError, ValueError) as exc:
            logger.error("Failed to tag '%s': %s", product.product_id, exc)
            record = {
                "product_id": product.product_id,
                "tags": None,
                "error": str(exc),
                "usage": {},
                "latency_s": round(time.perf_counter() - start, 3),
            }
        return record

    # ------------------------------------------------------------------ #
    # Batch flow with concurrency control
    # ------------------------------------------------------------------ #
    async def tag_batch(
        self,
        products: Iterable[ProductInput],
        output_path: Optional[Path] = None,
    ) -> list[dict]:
        """Tag many products concurrently; optionally append records as JSONL."""
        items = list(products)
        loop = asyncio.get_running_loop()
        semaphore = asyncio.Semaphore(self.max_concurrency)

        with ThreadPoolExecutor(max_workers=self.max_concurrency) as pool:
            async def _run(product: ProductInput) -> dict:
                async with semaphore:
                    return await loop.run_in_executor(pool, self.tag_one, product)

            results = list(await asyncio.gather(*(_run(p) for p in items)))

        if output_path is not None:
            save_jsonl(results, Path(output_path))
        return results

    def tag_batch_sync(
        self,
        products: Iterable[ProductInput],
        output_path: Optional[Path] = None,
    ) -> list[dict]:
        """Sync wrapper around `tag_batch` for CLIs and scripts."""
        return asyncio.run(self.tag_batch(products, output_path))

    def cost_summary(self) -> dict:
        """Aggregate token/cost stats for everything tagged so far."""
        return self.cost_tracker.summary()


def save_jsonl(records: Iterable[dict], output_path: Path) -> Path:
    """Persist result records as JSONL (one JSON object per line)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, default=str) + "\n")
    return output_path


def load_jsonl(input_path: Path) -> list[dict]:
    """Read a JSONL file into a list of dicts."""
    with Path(input_path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
