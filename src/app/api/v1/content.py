from fastapi import APIRouter, HTTPException, Body, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Optional
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ...core.services.text_generation import TextGenerationService
from ...core.services.image_generation import ImageGenerationService
from ...models import ContentReview  # Your SQLAlchemy model
from ...core.db.database import async_get_db  # Your DB session dependency

router = APIRouter()
templates = Jinja2Templates(directory="src/app/templates")

@router.post("/generate", response_model=Dict)
async def generate_content(
    prompt: str = Body(..., embed=True),
    output_filename: str = Body("generated_image.jpg", embed=True)
):
    text_service = TextGenerationService()
    image_service = ImageGenerationService()
    try:
        image_path = await image_service.generate_image(prompt, output_filename)
        generated_text = await text_service.generate_text(prompt, image_path=image_path)
        return {
            "text": generated_text,
            "image_path": image_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/edit", response_model=Dict)
async def edit_content(
    text: Dict = Body(..., embed=True),
    image_path: Optional[str] = Body(None, embed=True),
    db: AsyncSession = Depends(async_get_db)
):
    # Save or update the edited text and image_path in the database
    content = ContentReview(text=text, image_path=image_path)
    db.add(content)
    await db.commit()
    await db.refresh(content)
    return {
        "id": content.id,
        "text": content.text,
        "image_path": content.image_path
    }

@router.get("/review", response_class=HTMLResponse)
async def review_content(request: Request):
    return templates.TemplateResponse("review_content.html", {"request": request})
    return templates.TemplateResponse("review_content.html", {"request": request})
