"""Tests for the Phase 4 CLIs (single, batch, evaluate) with mocked pipeline."""

import csv
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from src.pipeline.tagging_pipeline import TaggingPipeline
from src.schemas.product import ProductInput
from src.tagger.base import BaseTagger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import tag_batch  # noqa: E402
import tag_single  # noqa: E402
import evaluate as evaluate_cli  # noqa: E402


class CliStubTagger(BaseTagger):
    """Offline tagger so CLI tests need no API keys."""

    provider = "stub"

    def __init__(self, **kwargs):
        kwargs.setdefault("config", {"model": "stub-model"})
        super().__init__(**kwargs)

    def _call_model(self, product, image_b64, mime, prompt):
        return json.dumps({"category": "apparel"}), {
            "input_tokens": 10, "output_tokens": 5, "latency_s": 0.1,
        }


def _record(pid="p1", latency=1.0, tags=None, error=None):
    return {
        "product_id": pid,
        "tags": tags or {"category": "apparel"},
        "error": error,
        "usage": {},
        "latency_s": latency,
    }


def _stub_pipeline(**kwargs) -> TaggingPipeline:
    return TaggingPipeline(tagger=CliStubTagger(), **kwargs)


def _product(tmp_path, product_id="p1") -> ProductInput:
    from PIL import Image

    img = tmp_path / f"{product_id}.jpg"
    Image.new("RGB", (16, 16), color="red").save(img, format="JPEG")
    return ProductInput(product_id=product_id, image_path=img, description="desc")


def test_tag_single_prints_record_and_returns_zero(tmp_path, capsys):
    product = _product(tmp_path)
    argv = ["--image", str(product.image_path), "--description", "desc",
            "--product-id", "p1"]
    with patch.object(tag_single, "build_pipeline", return_value=_stub_pipeline()):
        assert tag_single.main(argv) == 0
    out, _ = capsys.readouterr()
    assert '"product_id": "p1"' in out


def test_tag_single_returns_one_on_error(tmp_path):
    product = _product(tmp_path)
    argv = ["--image", str(product.image_path), "--description", "desc"]
    with patch.object(
        TaggingPipeline, "tag_one", return_value=_record(error="boom")
    ), patch.object(tag_single, "build_pipeline", return_value=_stub_pipeline()):
        assert tag_single.main(argv) == 1


def test_tag_batch_csv_end_to_end(tmp_path):
    product = _product(tmp_path)
    input_csv = tmp_path / "in.csv"
    output = tmp_path / "out.jsonl"
    with input_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["product_id", "image", "description"]
        )
        writer.writeheader()
        writer.writerow(
            {"product_id": "p1", "image": product.image_path.name, "description": "x"}
        )
    argv = ["--input", str(input_csv), "--output", str(output)]
    with patch.object(tag_batch, "build_pipeline", return_value=_stub_pipeline()):
        assert tag_batch.main(argv) == 0
    assert json.loads(output.read_text(encoding="utf-8").splitlines()[0])["product_id"] == "p1"


def test_tag_batch_supports_jsonl(tmp_path):
    product = _product(tmp_path, "p9")
    input_jsonl = tmp_path / "in.jsonl"
    output = tmp_path / "out.jsonl"
    input_jsonl.write_text(
        json.dumps({"product_id": "p9", "image": product.image_path.name}) + "\n",
        encoding="utf-8",
    )
    argv = ["--input", str(input_jsonl), "--output", str(output)]
    with patch.object(tag_batch, "build_pipeline", return_value=_stub_pipeline()):
        assert tag_batch.main(argv) == 0


def test_tag_batch_rejects_unknown_format(tmp_path):
    bad = tmp_path / "in.txt"
    bad.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported input format"):
        tag_batch.load_products(bad)


def test_tag_batch_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        tag_batch.load_products(tmp_path / "nope.csv")


def test_evaluate_cli_aligns_by_product_id(tmp_path, capsys):
    preds = tmp_path / "preds.jsonl"
    truths = tmp_path / "truths.jsonl"
    tags = {"category": "apparel", "subcategory": "t-shirt"}
    preds.write_text(
        json.dumps({"product_id": "p1", "tags": tags, "latency_s": 1.0}) + "\n",
        encoding="utf-8",
    )
    truths.write_text(json.dumps({"product_id": "p1", "tags": tags}) + "\n", encoding="utf-8")
    report_path = tmp_path / "report.json"
    rc = evaluate_cli.main(
        ["--predictions", str(preds), "--ground-truth", str(truths),
         "--output", str(report_path)]
    )
    assert rc == 0
    out, _ = capsys.readouterr()
    assert '"exact_match_ratio": 1.0' in out
    assert json.loads(report_path.read_text(encoding="utf-8"))["n"] == 1
