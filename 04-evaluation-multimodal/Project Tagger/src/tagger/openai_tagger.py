"""GPT-4V / GPT-4o tagger via the `openai` SDK with JSON mode (lazy import)."""

from typing import Optional

from src.schemas.product import ProductInput
from src.tagger.base import BaseTagger, timed_call


class OpenAITagger(BaseTagger):
    """Product tagger backed by OpenAI vision models (JSON response format)."""

    provider = "openai"

    def __init__(self, config: Optional[dict] = None, **kwargs) -> None:
        super().__init__(config, **kwargs)
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "openai is not installed. Run: pip install openai"
            ) from exc
        api_key = self.config.get("api_key")
        if not api_key or api_key.startswith("your_") or "${" in api_key:
            raise ValueError(
                "Missing OpenAI API key. Set OPENAI_API_KEY in your environment."
            )
        self._client = OpenAI(api_key=api_key)

    def _call_model(
        self, product: ProductInput, image_b64: str, mime: str, prompt: str
    ) -> tuple[str, dict]:
        messages = [
            {"role": "system", "content": self._system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{image_b64}"
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        (response, latency) = timed_call(
            self._client.chat.completions.create,
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            top_p=self.config.get("top_p", 0.9),
            max_tokens=self.config.get("max_tokens", 1000),
            response_format={"type": "json_object"},
        )
        choice = response.choices[0].message.content or ""
        usage = response.usage
        return choice, {
            "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
            "latency_s": round(latency, 3),
        }
