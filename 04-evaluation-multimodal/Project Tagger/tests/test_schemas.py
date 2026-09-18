"""Tests for ProductInput / ProductTags schemas and validation rules."""

import pytest
from pydantic import ValidationError

from src.schemas.product import ProductInput
from src.schemas.tags import ProductTags


def test_product_input_requires_image():
    with pytest.raises(ValidationError):
        ProductInput(product_id="p1", description="no image")


def test_product_input_accepts_path_or_base64():
    assert ProductInput(product_id="p1", image_path="a.jpg").product_id == "p1"
    assert ProductInput(product_id="p2", image_base64="aGVsbG8=").product_id == "p2"


def test_tags_require_category_or_subcategory():
    with pytest.raises(ValidationError):
        ProductTags(color=["red"])
    assert ProductTags(subcategory="sneakers").subcategory == "sneakers"


def test_tags_normalization():
    tags = ProductTags(category=" Apparel ", color=["Red", "red", "BLUE"], brand=" Nike ")
    assert tags.category == "apparel"
    assert tags.color == ["red", "blue"]  # lowercased + de-duplicated
    assert tags.brand == "Nike"  # proper noun casing preserved


def test_tags_coerces_scalar_color_from_vlm():
    """Regression: Gemini returned 'Blue' instead of ['Blue'] (list_type error)."""
    tags = ProductTags(category="apparel", color="Blue")
    assert tags.color == ["blue"]


def test_tags_coerces_comma_separated_color():
    tags = ProductTags(category="apparel", color="Blue, Black")
    assert tags.color == ["blue", "black"]


def test_tags_coerces_list_to_scalar():
    tags = ProductTags(category=["Apparel"], subcategory=["T-Shirt"])
    assert tags.category == "apparel"
    assert tags.subcategory == "t-shirt"
