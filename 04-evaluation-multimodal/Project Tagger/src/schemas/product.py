"""Product input schema for multimodal tagging."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ProductInput(BaseModel):
    """A single product to tag: image + description.

    Either `image_path` or `image_base64` must be provided; `description`
    is optional but strongly recommended (the plan's prompt template
    references it).
    """

    product_id: str = Field(..., description="Unique product identifier")
    image_path: Optional[Path] = Field(
        None, description="Path to the product image file"
    )
    image_base64: Optional[str] = Field(
        None, description="Base64-encoded image bytes (alternative to image_path)"
    )
    description: Optional[str] = Field(
        None, description="Free-text product description"
    )

    def model_post_init(self, __context) -> None:
        if not self.image_path and not self.image_base64:
            raise ValueError("Either 'image_path' or 'image_base64' must be provided.")
