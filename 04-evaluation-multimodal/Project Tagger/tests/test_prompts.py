"""Tests for prompt loading / rendering (incl. few-shot support)."""

from src.prompts.loader import (
    load_few_shot_examples,
    load_system_prompt,
    render_user_prompt,
)


def test_system_prompt_mentions_json():
    prompt = load_system_prompt()
    assert "JSON" in prompt
    assert "product" in prompt.lower()


def test_user_prompt_includes_description():
    rendered = render_user_prompt("Red cotton t-shirt")
    assert "Red cotton t-shirt" in rendered
    assert "{description}" not in rendered


def test_user_prompt_without_examples_has_no_demo_block():
    rendered = render_user_prompt("A hat")
    assert "Example 1" not in rendered


def test_user_prompt_with_few_shot_examples():
    examples = [
        {
            "description": "Blue denim jacket",
            "image_note": "[image: blue jacket]",
            "tags": {"category": "apparel", "color": ["blue"]},
        }
    ]
    rendered = render_user_prompt("Green jacket", few_shot_examples=examples)
    assert "Green jacket" in rendered
    assert "Example 1" in rendered
    assert "Blue denim jacket" in rendered
    assert '"category": "apparel"' in rendered


def test_user_prompt_respects_max_examples():
    examples = [
        {"description": f"item {i}", "tags": {"category": "apparel"}} for i in range(5)
    ]
    rendered = render_user_prompt("query", few_shot_examples=examples, max_examples=2)
    assert "Example 2" in rendered
    assert "Example 3" not in rendered


def test_load_few_shot_examples_from_config():
    examples = load_few_shot_examples()
    assert len(examples) >= 1
    assert "description" in examples[0] and "tags" in examples[0]


def test_load_few_shot_examples_missing_file_returns_empty(tmp_path):
    assert load_few_shot_examples(prompts_dir=tmp_path) == []

