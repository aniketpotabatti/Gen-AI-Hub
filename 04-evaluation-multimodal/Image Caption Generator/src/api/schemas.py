# Pydantic schemas for API requests/responses
from pydantic import BaseModel
from typing import Optional

class CaptionRequest(BaseModel):
    image: str  # base64 encoded
    language: Optional[str] = "en"
    style: Optional[str] = None

class CaptionResponse(BaseModel):
    caption: str