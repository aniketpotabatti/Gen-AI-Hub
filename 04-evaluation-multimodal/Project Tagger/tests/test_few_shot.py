"""Tests that BaseTagger forwards few-shot examples into the prompt."""

import json
from unittest.mock import patch

from src.schemas.product import ProductInput
from src.tagger.base import BaseTagger


class FewShotStub(BaseTagger):
    """Offline stub mirroring tests/test_taggers.py::StubTagger."""

    provider = "stub"

    def __init__(self, **kwargs):
        kwargs.setdefault("config", {"model": "stub-model"})
        super().__init__(**kwargs)

    def _call_model(self, product, image_b64, mime, prompt):
        return json.dumps({"category": "apparel", "subcategory": "jacket"}), {
            "input_tokens": 10, "output_tokens": 5, "latency_s": 0.1,
        }


PRODUCT = ProductInput(
    product_id="p1",
    image_path="tests/fixtures/sample_image.jpg",
    description="Blue jacket",
)


def test_tagger_without_few_shot_has_plain_prompt():
    tagger = FewShotStub()
    assert tagger.few_shot_examples == []
    with patch.object(
        FewShotStub, "_call_model", autospec=True,
        return_value=(json.dumps({"category": "apparel", "subcategory": "jacket"}),
                      {"input_tokens": 10, "output_tokens": 5, "latency_s": 0.1}),
    ) as mocked:
        tagger.tag_product(PRODUCT)
    # autospec includes `self` as args[0]; prompt is the last positional arg.
    assert "Example 1" not in mocked.call_args[0][-1]


def test_tagger_with_explicit_few_shot_appends_examples():
    tagger = FewShotStub(
        few_shot_examples=[{"description": "demo item", "tags": {"category": "apparel"}}]
    )
    with patch.object(
        FewShotStub, "_call_model", autospec=True,
        return_value=(json.dumps({"category": "apparel", "subcategory": "jacket"}),
                      {"input_tokens": 10, "output_tokens": 5, "latency_s": 0.1}),
    ) as mocked:
        tagger.tag_product(PRODUCT)
    prompt = mocked.call_args[0][-1]
    assert "Example 1" in prompt and "demo item" in prompt


def test_tagger_use_few_shot_loads_config_file():
    tagger = FewShotStub(use_few_shot=True)
    assert len(tagger.few_shot_examples) >= 1
    with patch.object(
        FewShotStub, "_call_model", autospec=True,
        return_value=(json.dumps({"category": "apparel", "subcategory": "jacket"}),
                      {"input_tokens": 10, "output_tokens": 5, "latency_s": 0.1}),
    ) as mocked:
        tagger.tag_product(PRODUCT)
    assert "Example 1" in mocked.call_args[0][-1]
