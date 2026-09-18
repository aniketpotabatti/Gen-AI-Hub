"""Local VLM tagger via Ollama (LLaVA, Qwen2-VL, ...) with lazy import.

Falls back to an OpenAI-compatible `/v1/chat/completions` endpoint (vLLM)
when the `ollama` package is unavailable but `vllm_base_url` is configured.
"""

import base64
import urllib.request

from src.schemas.product import ProductInput
from src.tagger.base import BaseTagger, timed_call


class LocalTagger(BaseTagger):
    """Product tagger backed by a local vision model (Ollama or vLLM)."""

    provider = "local"

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._base_url = self.config.get("base_url", "http://localhost:11434")
        self._vllm_url = self.config.get("vllm_base_url")
        try:
            import ollama  # type: ignore
            self._ollama = ollama.Client(host=self._base_url)
            self._backend = "ollama"
        except ImportError:
            if not self._vllm_url:
                raise ImportError(
                    "ollama is not installed. Run: pip install ollama "
                    "(or set 'vllm_base_url' in models.yaml to use vLLM)."
                )
            self._ollama = None
            self._backend = "vllm"

    def _call_model(
        self, product: ProductInput, image_b64: str, mime: str, prompt: str
    ) -> tuple[str, dict]:
        base64.b64decode(image_b64, validate=True)
        if self._backend == "ollama":
            return self._call_ollama(image_b64, prompt)
        return self._call_vllm(image_b64, mime, prompt)

    def _call_ollama(self, image_b64: str, prompt: str) -> tuple[str, dict]:
        response, latency = timed_call(
            self._ollama.chat,
            model=self.model,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": prompt, "images": [image_b64]},
            ],
            options={
                "temperature": self.temperature,
                "top_p": self.config.get("top_p", 0.9),
                "num_predict": self.config.get("num_predict", 1000),
            },
            format="json",
        )
        text = response.get("message", {}).get("content", "")
        return text, {
            "input_tokens": 0,  # Ollama rarely reports token counts
            "output_tokens": max(len(text) // 4, 0),
            "latency_s": round(latency, 3),
        }

    def _call_vllm(self, image_b64: str, mime: str, prompt: str) -> tuple[str, dict]:
        import json as _json

        payload = _json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                            {"type": "text", "text": prompt},
                        ],
                    },
                ],
                "temperature": self.temperature,
                "top_p": self.config.get("top_p", 0.9),
                "max_tokens": self.config.get("num_predict", 1000),
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self._vllm_url.rstrip('/')}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        raw, latency = timed_call(urllib.request.urlopen, request, timeout=300)
        body = _json.loads(raw.read().decode("utf-8"))
        usage = body.get("usage", {})
        return body["choices"][0]["message"]["content"] or "", {
            "input_tokens": usage.get("prompt_tokens", 0) or 0,
            "output_tokens": usage.get("completion_tokens", 0) or 0,
            "latency_s": round(latency, 3),
        }

