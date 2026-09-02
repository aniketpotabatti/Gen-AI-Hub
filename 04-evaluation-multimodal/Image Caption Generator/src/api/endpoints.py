# API endpoints for caption generation
from fastapi import APIRouter, HTTPException
from ..models.image_caption_model import ImageCaptionModel
from ..schemas import CaptionRequest, CaptionResponse

router = APIRouter()
model = ImageCaptionModel()

@router.post("/caption", response_model=CaptionResponse)
async def generate_caption(request: CaptionRequest):
    try:
        # decode base64 image, generate caption
        caption = model.generate(request.image, language=request.language, style=request.style)
        return CaptionResponse(caption=caption)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))