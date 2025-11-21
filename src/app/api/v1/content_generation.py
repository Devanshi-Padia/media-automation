from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import Dict, Any
import os
from ..dependencies import get_current_user
from ...models.user import User
from ...schemas.content import ContentGenerationRequest, ContentGenerationResponse
from ...core.services.text_generation import TextGenerationService
from ...core.services.image_generation import ImageGenerationService
from ...core.services.social_media import SocialMediaService
import time

router = APIRouter(prefix="/content", tags=["content-generation"])

@router.post("/generate", response_model=ContentGenerationResponse)
async def generate_content(
    request: ContentGenerationRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate content (text and image) based on a prompt."""
    try:
        text_service = TextGenerationService()
        image_service = ImageGenerationService()
        
        # Generate text for all platforms
        generated_text = await text_service.generate_text(request.prompt)
        
        # Generate base image and platform-specific templates
        image_templates = await image_service.generate_image(
            request.prompt, 
            f"generated_{current_user.id}_{int(time.time())}.png"
        )
        
        return ContentGenerationResponse(
            text=generated_text,
            image_paths=image_templates,  # Now returns dict of platform-specific images
            prompt=request.prompt
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/post-to-social-media")
async def post_to_social_media(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Post generated content to social media platforms.
    """
    try:
        social_service = SocialMediaService()
        text = request.get("text")
        image_path = request.get("image_path")
        if not isinstance(text, dict) or not isinstance(image_path, str):
            raise HTTPException(status_code=400, detail="Invalid request: 'text' must be a dict and 'image_path' must be a string.")
        result = await social_service.post_to_social_media(
            text,
            image_path
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/image/{filename}")
async def get_generated_image(filename: str):
    """
    Serve generated images.
    """
    image_path = os.path.join("public", "generated_images", filename)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(image_path)