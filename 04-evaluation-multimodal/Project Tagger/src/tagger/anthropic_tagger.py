"""Claude tagger via the `anthropic` SDK (lazy import)."""

import base64
from typing import Optional

from src.schemas.product import ProductInput
from src.tagger.base import BaseTagger, timed_call

_ANTHROPIC_MEDIA = {
    "image/jpeg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
}


class AnthropicTagger(BaseTagger):
    """Product tagger backed by Claude vision models."""

    provider = "anthropic"

    def __init__(self, config: Optional[dict] = None, **kwargs) -> None:
        super().__init__(config, **kwargs)
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "anthropic is not installed. Run: pip install anthropic"
            ) from exc
        api_key = self.config.get("api_key")
        if not api_key or api_key.startswith("your_") or "${" in api_key:
            raise ValueError(
                "Missing Anthropic API key. Set ANTHROPIC_API_KEY in your environment."
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    def _call_model(
        self, product: ProductInput, image_b64: str, mime: str, prompt: str
    ) -> tuple[str, dict]:
        # Anthropic accepts base64 source blocks; validate early for a clear error.
        base64.b64decode(image_b64, validate=True)
        (response, latency) = timed_call(
            self._client.messages.create,
            model=self.model,
            system=self._system_prompt,
            max_tokens=self.config.get("max_tokens", 1000),
            temperature=self.temperature,
            top_p=self.config.get("top_p", 0.9),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": _ANTHROPIC_MEDIA.get(mime, "image/jpeg"),
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        usage = response.usage
        return text, {
            "input_tokens": getattr(usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            "latency_s": round(latency, 3),
        }
