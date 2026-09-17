"""Gemini 2.5 Flash tagger via the `google-genai` SDK (lazy import)."""

from typing import Optional

from src.schemas.product import ProductInput
from src.tagger.base import BaseTagger, timed_call


class GeminiTagger(BaseTagger):
    """Product tagger backed by Gemini 2.5 Flash."""

    provider = "gemini"

    def __init__(self, config: Optional[dict] = None, **kwargs) -> None:
        super().__init__(config, **kwargs)
        try:
            from google import genai  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "google-genai is not installed. Run: pip install google-genai"
            ) from exc
        api_key = self.config.get("api_key")
        if not api_key or api_key.startswith("your_") or "${" in api_key:
            raise ValueError(
                "Missing Gemini API key. Set GEMINI_API_KEY in your environment."
            )
        self._client = genai.Client(api_key=api_key)

    def _call_model(
        self, product: ProductInput, image_b64: str, mime: str, prompt: str
    ) -> tuple[str, dict]:
        from google.genai import types  # type: ignore

        contents = [
            types.Part.from_bytes(data=image_b64, mime_type=mime),
            prompt,
        ]
        gen_config = types.GenerateContentConfig(
            system_instruction=self._system_prompt,
            temperature=self.temperature,
            top_p=self.config.get("top_p", 0.9),
            max_output_tokens=self.config.get("max_output_tokens", 1000),
            response_mime_type="application/json",
        )
        (response, latency) = timed_call(
            self._client.models.generate_content,
            model=self.model,
            contents=contents,
            config=gen_config,
        )
        usage_meta = getattr(response, "usage_metadata", None)
        usage = {
            "input_tokens": getattr(usage_meta, "prompt_token_count", 0) or 0,
            "output_tokens": getattr(usage_meta, "candidates_token_count", 0) or 0,
            "latency_s": round(latency, 3),
        }
        return response.text or "", usage
