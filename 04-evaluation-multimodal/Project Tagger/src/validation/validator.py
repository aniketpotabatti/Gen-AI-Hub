"""Standalone JSON schema validation against the `ProductTags` model.

The taggers already validate inline during their retry loop; this module
exposes the same logic for the pipeline, CLIs, and evaluation scripts that
need to validate externally produced JSON (e.g. cached or human-annotated).
"""

import json
from typing import Any, Union

from pydantic import ValidationError

from src.schemas.tags import ProductTags
from src.tagger.base import extract_json_block


class ValidationResult:
    """Outcome of validating one raw JSON payload."""

    def __init__(
        self,
        ok: bool,
        tags: Union[ProductTags, None] = None,
        errors: Union[list, None] = None,
    ) -> None:
        self.ok = ok
        self.tags = tags
        self.errors = errors or []

    def __bool__(self) -> bool:
        return self.ok


def validate_tags(raw: Union[str, dict]) -> ValidationResult:
    """Validate a raw VLM response (JSON string or dict) as `ProductTags`.

    Tolerates markdown fences and surrounding commentary via
    `extract_json_block` before parsing.
    """
    try:
        payload: Any = json.loads(extract_json_block(raw)) if isinstance(raw, str) else raw
        return ValidationResult(ok=True, tags=ProductTags.model_validate(payload))
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            errors = [
                {"field": ".".join(map(str, err["loc"])), "message": err["msg"]}
                for err in exc.errors()
            ]
        else:
            errors = [{"field": "", "message": f"Invalid JSON: {exc}"}]
        return ValidationResult(ok=False, errors=errors)
