"""Mock-based unit tests for taggers, validation, pipeline, and cost tracking."""

import asyncio
import json

import pytest

from src.pipeline.tagging_pipeline import TaggingPipeline, load_jsonl, save_jsonl
from src.schemas.product import ProductInput
from src.tagger.base import BaseTagger, TaggingError
from src.tagger.factory import available_providers, create_tagger
from src.utils.cost_tracker import CostTracker, estimate_cost
from src.utils.json_utils import extract_json_block
from src.validation.validator import validate_tags

VALID_JSON = '{"category": "apparel", "color": ["red"], "brand": "Nike"}'
FENCED_JSON = '```json\n{"category": "footwear"}\n```'


class StubTagger(BaseTagger):
    """In-memory tagger: returns canned responses without network calls."""

    provider = "stub"

    def __init__(self, responses, **kwargs):
        kwargs.setdefault("config", {"model": "stub-model"})
        super().__init__(**kwargs)
        self._responses = list(responses)
        self.calls = 0

    def _call_model(self, product, image_b64, mime, prompt):
        self.calls += 1
        assert image_b64 and mime.startswith("image/")
        assert product.product_id
        response = self._responses[min(self.calls - 1, len(self._responses) - 1)]
        if isinstance(response, Exception):
            raise response
        assert isinstance(response, str), "Stub responses must be raw JSON strings"
        return response, {"input_tokens": 100, "output_tokens": 50}


def _product(tmp_path, product_id="p1"):
    from PIL import Image

    img_path = tmp_path / f"{product_id}.jpg"
    Image.new("RGB", (32, 32), color="red").save(img_path, format="JPEG")
    return ProductInput(
        product_id=product_id, image_path=img_path, description="Red shirt"
    )


# --- base helpers ----------------------------------------------------- #


def test_extract_json_block_strips_fences():
    assert json.loads(extract_json_block(FENCED_JSON))["category"] == "footwear"
    assert json.loads(extract_json_block("prefix " + VALID_JSON + " suffix"))["brand"] == "Nike"


def test_retry_on_transport_error_then_succeeds(tmp_path):
    tagger = StubTagger([TimeoutError("boom"), VALID_JSON])
    tags = tagger.tag_product(_product(tmp_path))
    assert tags.category == "apparel"
    assert tagger.calls == 2


def test_validation_retry_with_format_nudge(tmp_path):
    tagger = StubTagger(["not json at all", VALID_JSON])
    tags = tagger.tag_product(_product(tmp_path))
    assert tags.brand == "Nike"
    assert tagger.calls == 2


def test_tagging_error_after_all_attempts_fail(tmp_path):
    tagger = StubTagger(["garbage", "still garbage", "more garbage"])
    with pytest.raises(TaggingError):
        tagger.tag_product(_product(tmp_path))


# --- factory ---------------------------------------------------------- #


def test_available_providers():
    assert available_providers() == ["anthropic", "gemini", "local", "openai"]


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unknown provider"):
        create_tagger(provider="nonexistent")


def test_factory_missing_api_key_raises_clear_error():
    with pytest.raises(ValueError, match="API key"):
        create_tagger(provider="gemini")


# --- validator + cost tracker ----------------------------------------- #


def test_validate_tags_accepts_dict_and_string():
    assert validate_tags({"category": "apparel"}).ok
    assert validate_tags(FENCED_JSON).ok
    bad = validate_tags('{"color": ["red"]}')  # missing category/subcategory
    assert not bad
    assert bad.errors


def test_cost_tracker_accumulates():
    tracker = CostTracker()
    tracker.record("openai", "gpt-4o", {"input_tokens": 1000, "output_tokens": 500})
    tracker.record("local", "llava:latest", {"input_tokens": 100, "output_tokens": 50})
    summary = tracker.summary()
    assert summary["requests"] == 2
    assert summary["total_input_tokens"] == 1100
    assert summary["by_model"]["openai/gpt-4o"]["requests"] == 1
    assert estimate_cost("openai", "gpt-4o", {"input_tokens": 1_000_000, "output_tokens": 0}) == 2.5
    assert estimate_cost("local", "llava:latest", {"input_tokens": 999, "output_tokens": 999}) == 0.0


# --- pipeline --------------------------------------------------------- #


def test_pipeline_tag_one_success_and_failure(tmp_path):
    pipeline = TaggingPipeline(tagger=StubTagger([VALID_JSON]))
    record = pipeline.tag_one(_product(tmp_path))
    assert record["tags"]["category"] == "apparel"
    assert record["error"] is None

    bad_product = ProductInput(product_id="bad", image_path=tmp_path / "missing.jpg")
    failed = pipeline.tag_one(bad_product)
    assert failed["tags"] is None
    assert failed["error"]


def test_pipeline_batch_and_jsonl_persistence(tmp_path):
    products = [_product(tmp_path, f"p{i}") for i in range(3)]
    out_path = tmp_path / "out" / "results.jsonl"
    pipeline = TaggingPipeline(
        tagger=StubTagger([VALID_JSON]),
        max_concurrency=2,
    )
    results = asyncio.run(pipeline.tag_batch(products, out_path))
    assert len(results) == 3
    assert all(r["tags"]["category"] == "apparel" for r in results)
    assert len(load_jsonl(out_path)) == 3
    assert pipeline.cost_summary()["requests"] == 3


def test_save_jsonl_roundtrip(tmp_path):
    path = save_jsonl([{"a": 1}, {"b": 2}], tmp_path / "r.jsonl")
    assert [r["a"] if "a" in r else r["b"] for r in load_jsonl(path)] == [1, 2]
