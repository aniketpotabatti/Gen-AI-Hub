"""Token usage and cost estimation per VLM request (plan Phase 2 item)."""

from dataclasses import dataclass, field

# USD per 1M tokens. Cloud prices are approximate list prices at time of
# writing; local inference is treated as free (electricity/hardware excluded).
PRICE_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "llava:latest": {"input": 0.0, "output": 0.0},
}

# Fallback prices per provider when the exact model is not in the table.
PROVIDER_FALLBACK_MODEL: dict[str, str] = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20241022",
    "local": "llava:latest",
}


def _price_key(provider: str, model: str) -> str:
    if model in PRICE_PER_1M_TOKENS:
        return model
    return PROVIDER_FALLBACK_MODEL.get(provider, "llava:latest")


def estimate_cost(provider: str, model: str, usage: dict) -> float:
    """Estimate request cost in USD from a usage dict.

    `usage` uses OpenAI-style keys: `{"input_tokens": int, "output_tokens": int}`.
    Unknown models fall back to the provider default; unknown providers cost 0.
    """
    key = _price_key(provider, model)
    prices = PRICE_PER_1M_TOKENS.get(key, {"input": 0.0, "output": 0.0})
    input_tokens = usage.get("input_tokens", 0) or 0
    output_tokens = usage.get("output_tokens", 0) or 0
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000


@dataclass
class CostTracker:
    """Accumulates token usage and cost across tagging requests."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    requests: int = 0
    _by_model: dict = field(default_factory=dict, repr=False)

    def record(self, provider: str, model: str, usage: dict) -> float:
        """Record one request; returns its estimated cost in USD."""
        cost = estimate_cost(provider, model, usage)
        self.total_input_tokens += usage.get("input_tokens", 0) or 0
        self.total_output_tokens += usage.get("output_tokens", 0) or 0
        self.total_cost_usd += cost
        self.requests += 1
        key = f"{provider}/{model}"
        entry = self._by_model.setdefault(
            key, {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
        )
        entry["requests"] += 1
        entry["input_tokens"] += usage.get("input_tokens", 0) or 0
        entry["output_tokens"] += usage.get("output_tokens", 0) or 0
        entry["cost_usd"] += cost
        return cost

    def summary(self) -> dict:
        """Return aggregate stats (plan Phase 2: average cost per product)."""
        avg = self.total_cost_usd / self.requests if self.requests else 0.0
        return {
            "requests": self.requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "avg_cost_usd_per_product": round(avg, 6),
            "by_model": dict(self._by_model),
        }
