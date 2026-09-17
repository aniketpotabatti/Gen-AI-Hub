"""Abstract base class for all VLM product taggers.

Every tagger follows the same contract:
  1. Build prompts (system + rendered user prompt).
  2. Call the model with exponential-backoff retries on transport errors
     (tenacity), then validate the JSON against `ProductTags`, retrying with a
     stricter format nudge on `ValidationError` (max 3 attempts per plan).
  3. Record token usage + cost via `CostTracker`.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.prompts.loader import (
    load_few_shot_examples,
    load_system_prompt,
    render_user_prompt,
)
from src.schemas.product import ProductInput
from src.schemas.tags import ProductTags
from src.utils.cost_tracker import CostTracker
from src.utils.image_utils import resolve_image

logger = logging.getLogger(__name__)

MAX_VALIDATION_ATTEMPTS = 3
FORMAT_NUDGE = (
    "\n\nIMPORTANT: Your previous response was not valid JSON matching the "
    "ProductTags schema. Respond with valid JSON only — no markdown fences, "
    "no commentary — and include at least 'category' or 'subcategory'."
)


class TaggingError(RuntimeError):
    """Raised when a product cannot be tagged after all retries."""


class BaseTagger(ABC):
    """Shared tagging flow; subclasses only implement `_call_model()`."""

    provider: str = "base"

    def __init__(
        self,
        config: Optional[dict] = None,
        cost_tracker: Optional[CostTracker] = None,
        max_image_dim: int = 1024,
        few_shot_examples: Optional[list[dict[str, Any]]] = None,
        use_few_shot: bool = False,
    ) -> None:
        self.config = config or {}
        self.model = self.config.get("model", "unknown")
        self.temperature = self.config.get("temperature", 0.2)
        self.cost_tracker = cost_tracker or CostTracker()
        self.max_image_dim = max_image_dim
        self._system_prompt = load_system_prompt()
        # Few-shot demonstrations (plan Phase 4): explicit list wins, else fall
        # back to config/prompts/few_shot_examples.json when enabled.
        if few_shot_examples is None and use_few_shot:
            few_shot_examples = load_few_shot_examples()
        self.few_shot_examples = list(few_shot_examples or [])
        self.last_usage: dict = {}

    # ------------------------------------------------------------------ #
    # Template methods
    # ------------------------------------------------------------------ #
    def tag_product(self, product: ProductInput) -> ProductTags:
        """Tag one product: call model -> validate -> retry on failure."""
        image_b64, mime = resolve_image(product, max_dim=self.max_image_dim)
        user_prompt = render_user_prompt(
            product.description or "",
            few_shot_examples=self.few_shot_examples or None,
        )
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
            prompt = user_prompt + (FORMAT_NUDGE if attempt > 1 else "")
            try:
                raw_text, usage = self._call_model_with_retry(
                    product, image_b64, mime, prompt
                )
            except Exception as exc:  # noqa: BLE001 - wrapped below
                last_error = exc
                logger.warning(
                    "[%s] model call failed (attempt %d/%d): %s",
                    self.provider, attempt, MAX_VALIDATION_ATTEMPTS, exc,
                )
                continue

            self.last_usage = usage
            self.cost_tracker.record(self.provider, self.model, usage)
            try:
                return ProductTags.model_validate(_parse_json(raw_text))
            except (ValidationError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "[%s] validation failed (attempt %d/%d): %s",
                    self.provider, attempt, MAX_VALIDATION_ATTEMPTS, exc,
                )

        raise TaggingError(
            f"[{self.provider}] failed to tag '{product.product_id}' "
            f"after {MAX_VALIDATION_ATTEMPTS} attempts: {last_error}"
        )

    # ------------------------------------------------------------------ #
    # Retry wrapper (transport-level: timeouts, rate limits, 5xx).
    # ------------------------------------------------------------------ #
    def _call_model_with_retry(
        self, product: ProductInput, image_b64: str, mime: str, prompt: str
    ) -> tuple[str, dict]:
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((TimeoutError, ConnectionError)),
            reraise=True,
        )
        def _call() -> tuple[str, dict]:
            return self._call_model(product, image_b64, mime, prompt)

        return _call()

    @abstractmethod
    def _call_model(
        self, product: ProductInput, image_b64: str, mime: str, prompt: str
    ) -> tuple[str, dict]:
        """Call the VLM; return `(raw_text_response, usage_dict)`.

        `usage_dict` uses OpenAI-style keys:
        `{"input_tokens": int, "output_tokens": int, "latency_s": float}`.
        """


def extract_json_block(text: str) -> str:
    """Strip markdown fences / commentary, returning the JSON payload."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]  # drop opening fence (```json or ```)
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def _parse_json(text: str) -> Any:
    return json.loads(extract_json_block(text))


def timed_call(func, *args, **kwargs) -> tuple[Any, float]:
    """Run `func` and return `(result, elapsed_seconds)`."""
    start = time.perf_counter()
    return func(*args, **kwargs), time.perf_counter() - start
