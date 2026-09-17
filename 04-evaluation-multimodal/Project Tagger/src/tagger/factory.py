"""Provider-agnostic factory for instantiating taggers from `models.yaml`."""

from typing import Optional

from src.config import load_models_config
from src.tagger.anthropic_tagger import AnthropicTagger
from src.tagger.base import BaseTagger
from src.tagger.gemini_tagger import GeminiTagger
from src.tagger.local_tagger import LocalTagger
from src.tagger.openai_tagger import OpenAITagger
from src.utils.cost_tracker import CostTracker

_TAGGERS: dict[str, type[BaseTagger]] = {
    "gemini": GeminiTagger,
    "openai": OpenAITagger,
    "anthropic": AnthropicTagger,
    "local": LocalTagger,
}


def available_providers() -> list[str]:
    """Return the sorted list of supported provider names."""
    return sorted(_TAGGERS)


def create_tagger(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    cost_tracker: Optional[CostTracker] = None,
    **overrides,
) -> BaseTagger:
    """Instantiate a tagger by provider name.

    Args:
        provider: one of `available_providers()`; defaults to
            `default_provider` in models.yaml.
        model: optional model override (defaults to the provider's config).
        cost_tracker: shared tracker; a new one is created when omitted.
        **overrides: extra config keys merged over the provider's YAML block.

    Raises:
        ValueError: for unknown provider names.
    """
    cfg = load_models_config()
    provider = provider or cfg.get("default_provider", "gemini")
    if provider not in _TAGGERS:
        raise ValueError(
            f"Unknown provider '{provider}'. Available: {available_providers()}"
        )
    provider_cfg = dict(cfg.get("providers", {}).get(provider, {}))
    if model:
        provider_cfg["model"] = model
    tagger_kwargs = {}
    for key in ("few_shot_examples", "use_few_shot", "max_image_dim"):
        if key in overrides:
            tagger_kwargs[key] = overrides.pop(key)
    provider_cfg.update(overrides)
    return _TAGGERS[provider](
        config=provider_cfg,
        cost_tracker=cost_tracker or CostTracker(),
        **tagger_kwargs,
    )
