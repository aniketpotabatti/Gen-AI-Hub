"""Product output (tags) schema for multimodal tagging."""

from pydantic import BaseModel, Field, field_validator, model_validator

_LOWERCASE_FIELDS = ("category", "subcategory", "pattern", "gender", "age_group", "size")
_LIST_FIELDS = ("color", "material", "style", "usage_occasion")


class ProductTags(BaseModel):
    """Structured tags produced by a VLM for one product."""

    # Core identification
    category: str | None = Field(
        None, description="Primary product category (e.g. 'shoes', 'dress')"
    )
    subcategory: str | None = Field(
        None, description="Secondary classification (e.g. 'sneakers', 'cocktail dress')"
    )
    brand: str | None = Field(None, description="Brand name if visible or mentioned")

    # Visual attributes
    color: list[str] | None = Field(
        None, description="Observed colors (e.g. ['red', 'black'])"
    )
    material: list[str] | None = Field(
        None, description="Materials (e.g. ['cotton', 'leather'])"
    )
    pattern: str | None = Field(
        None, description="Pattern (e.g. 'striped', 'floral', 'solid')"
    )
    style: list[str] | None = Field(
        None, description="Style tags (e.g. ['casual', 'formal', 'vintage'])"
    )

    # Target demographics
    gender: str | None = Field(
        None, description="Intended gender (e.g. 'men', 'women', 'unisex')"
    )
    age_group: str | None = Field(
        None, description="Age group (e.g. 'adult', 'youth', 'senior')"
    )

    # Usage & properties
    usage_occasion: list[str] | None = Field(
        None, description="Occasions (e.g. ['sports', 'party', 'work'])"
    )
    size: str | None = Field(None, description="Size if visible (e.g. 'M', '42')")
    is_waterproof: bool | None = Field(
        None, description="Whether the product is waterproof"
    )

    # Custom attributes (domain-specific extensions)
    custom_attributes: dict | None = Field(
        None, description="Additional domain-specific attributes"
    )

    @model_validator(mode="after")
    def _require_category_or_subcategory(self):
        if not self.category and not self.subcategory:
            raise ValueError(
                "At least one of 'category' or 'subcategory' must be present."
            )
        return self

    @field_validator(*_LIST_FIELDS, mode="before")
    @classmethod
    def _coerce_to_list(cls, value):
        """Tolerate VLMs returning a scalar where a list is expected.

        `"Blue"` -> `["Blue"]`; `"Blue, Black"` -> `["Blue", "Black"]`.
        Without this, a single-string response fails validation on all retries.
        """
        if value is None or isinstance(value, list):
            return value
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",") if part.strip()]
            return parts or None
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]

    @field_validator(*_LOWERCASE_FIELDS, "brand", mode="before")
    @classmethod
    def _coerce_to_scalar(cls, value):
        """Tolerate VLMs returning a one-element list where a scalar is expected."""
        if isinstance(value, list):
            return value[0] if value else None
        return value

    @field_validator(*_LOWERCASE_FIELDS)
    @classmethod
    def _normalize_string(cls, value):
        """Strip, drop empties, and lowercase taxonomy-like string fields.

        Brand names are proper nouns, so `brand` is intentionally excluded
        (stripped only) to preserve casing.
        """
        if value is None:
            return value
        value = value.strip()
        if not value:
            return None
        return value.lower()

    @field_validator("brand")
    @classmethod
    def _normalize_brand(cls, value):
        if value is None:
            return value
        value = value.strip()
        return value or None

    @field_validator("color", "material", "style", "usage_occasion")
    @classmethod
    def _normalize_lists(cls, values):
        """Lowercase, strip, and de-duplicate list fields (plan validation rules)."""
        if values is None:
            return values
        seen, normalized = set(), []
        for item in values:
            item = item.strip().lower()
            if item and item not in seen:
                seen.add(item)
                normalized.append(item)
        return normalized or None

