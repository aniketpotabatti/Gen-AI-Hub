"""Load prompt templates from config/prompts/."""

import json
from pathlib import Path
from typing import Any

DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "config" / "prompts"


def load_prompt(filename: str, prompts_dir: Path = DEFAULT_PROMPTS_DIR) -> str:
    """Read a prompt file and return its stripped contents."""
    path = Path(prompts_dir) / filename
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def load_system_prompt(prompts_dir: Path = DEFAULT_PROMPTS_DIR) -> str:
    """Load the VLM system prompt."""
    return load_prompt("system_prompt.txt", prompts_dir)


def render_user_prompt(
    description: str,
    prompts_dir: Path = DEFAULT_PROMPTS_DIR,
    few_shot_examples: list[dict[str, Any]] | None = None,
    max_examples: int = 3,
) -> str:
    """Render the user prompt template with a product description.

    When `few_shot_examples` is provided (each with `description` and `tags`
    keys, optionally `image_note`), up to `max_examples` are appended as
    text demonstrations to improve output consistency (plan Phase 4 item).
    Images can't be embedded in a plain-text few-shot block, so examples
    carry an `image_note` placeholder describing the image instead.
    """
    template = load_prompt("user_prompt_template.txt", prompts_dir)
    rendered = template.format(description=description or "")
    examples = list(few_shot_examples or [])[:max_examples]
    if not examples:
        return rendered
    blocks = []
    for i, example in enumerate(examples, 1):
        image_note = example.get("image_note", "[product image]")
        tags_json = json.dumps(example.get("tags", {}))
        blocks.append(
            f"Example {i}:\n"
            f"Image: {image_note}\n"
            f"Description: {example.get('description', '')}\n"
            f"Tags: {tags_json}"
        )
    return rendered + "\n\n" + "\n\n".join(blocks)


def load_few_shot_examples(
    prompts_dir: Path = DEFAULT_PROMPTS_DIR,
    filename: str = "few_shot_examples.json",
    max_examples: int = 3,
) -> list[dict[str, Any]]:
    """Load few-shot demonstrations; returns [] when the file is absent."""
    path = Path(prompts_dir) / filename
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as handle:
        examples = json.load(handle) or []
    return list(examples)[:max_examples]

