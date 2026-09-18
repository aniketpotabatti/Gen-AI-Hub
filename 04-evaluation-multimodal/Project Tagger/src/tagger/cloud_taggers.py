"""Cloud taggers (Anthropic, Gemini, OpenAI) via their respective SDKs (lazy import)."""

import base64

from src.schemas.product import ProductInput
from src.tagger.base import BaseTagger, timed_call
from src.utils.json_utils import extract_json_block


class AnthropicTagger(BaseTagger):
    """Product tagger backed by Claude vision models."""

    provider = "anthropic"

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config, **kwargs)
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "anthropic is not installed. Run: pip install anthropic"
            ) from exc
        self._client = anthropic.Anthropic(api_key=self._require_api_key("ANTHROPIC_API_KEY"))

    def _call_model(
        self, product: ProductInput, image_b64: str, mime: str, prompt: str
    ) -> tuple[str, dict]:
        # Validate base64 early for a clear error before the API call.
        base64.b64decode(image_b64, validate=True)
        # Anthropic media types we allow passthrough; otherwise default to JPEG.
        _ANTHROPIC_MEDIA = frozenset({"image/jpeg", "image/png", "image/webp"})
        media_type = mime if mime in _ANTHROPIC_MEDIA else "image/jpeg"

        response, latency = timed_call(
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
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                },
            ],
        )
        usage = response.usage
        text = "".join(block.text for block in response.content if block.type == "text")
        return text, {
            "input_tokens": getattr(usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            "latency_s": round(latency, 3),
        }


class GeminiTagger(BaseTagger):
    """Product tagger backed by Gemini 2.5 Flash."""

    provider = "gemini"

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config, **kwargs)
        try:
            from google import genai  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "google-genai is not installed. Run: pip install google-genai"
            ) from exc
        self._client = genai.Client(api_key=self._require_api_key("GEMINI_API_KEY"))

    def _call_model(
        self, product: ProductInput, image_b64: str, mime: str, prompt: str
    ) -> tuple[str, dict]:
        from google.genai import types  # type: ignore

        contents = [types.Part.from_bytes(data=image_b64, mime_type=mime), prompt]
        gen_config = types.GenerateContentConfig(
            system_instruction=self._system_prompt,
            temperature=self.temperature,
            top_p=self.config.get("top_p", 0.9),
            max_output_tokens=self.config.get("max_output_tokens", 1000),
            response_mime_type="application/json",
        )
        response, latency = timed_call(
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
        # Gemini may return JSON wrapped in markdown fences or extra text.
        raw = response.text or ""
        cleaned = extract_json_block(raw)
        return cleaned, usage


class OpenAITagger(BaseTagger):
    """Product tagger backed by OpenAI vision models (JSON response format)."""

    provider = "openai"

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config, **kwargs)
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:
            raise ImportError("openai is not installed. Run: pip install openai") from exc
        self._client = OpenAI(api_key=self._require_api_key("OPENAI_API_KEY"))

    def _call_model(
        self, product: ProductInput, image_b64: str, mime: str, prompt: str
    ) -> tuple[str, dict]:
        messages = [
            {"role": "system", "content": self._system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64:{image_b64}"}},
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        response, latency = timed_call(
            self._client.chat.completions.create,
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            top_p=self.config.get("top_p", 0.9),
            max_tokens=self.config.get("max_tokens", 1000),
            response_format={"type": "json_object"},
        )
        usage = response.usage
        return response.choices[0].message.content or "", {
            "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
            "latency_s": round(latency, 3),
        }
