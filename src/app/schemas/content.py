from pydantic import BaseModel, Field
from typing import Dict, Optional, List
from datetime import datetime

# Request/Response schemas for API
class ContentGenerationRequest(BaseModel):
    prompt: str = Field(..., description="The prompt for content generation")
    include_news: bool = Field(default=True, description="Whether to include latest blockchain news")
    platforms: Optional[list] = Field(default=None, description="Target social media platforms")

class ContentGenerationResponse(BaseModel):
    text: Dict[str, str] = Field(..., description="Generated text for different platforms")
    image_paths: Dict[str, str] = Field(..., description="Paths to platform-specific template images")
    prompt: str = Field(..., description="Original prompt used for generation")
    
class SocialMediaPostRequest(BaseModel):
    text: Dict[str, str] = Field(..., description="Text content for different platforms")
    image_path: str = Field(..., description="Path to the image to post")
    platforms: list = Field(..., description="List of platforms to post to")
    
class SocialMediaPostResponse(BaseModel):
    status: str = Field(..., description="Success status")
    successful_platforms: list = Field(..., description="List of successfully posted platforms")
    failed_platforms: list = Field(..., description="List of failed platforms")
    error: Optional[str] = Field(None, description="Error message if any")

# Database schemas for CRUD operations
class ContentGenerationCreate(BaseModel):
    prompt: str
    generated_text: Dict[str, str]
    image_path: Optional[str] = None
    include_news: bool = True
    platforms: Optional[List[str]] = None

class ContentGenerationUpdate(BaseModel):
    prompt: Optional[str] = None
    generated_text: Optional[Dict[str, str]] = None
    image_path: Optional[str] = None
    include_news: Optional[bool] = None
    platforms: Optional[List[str]] = None

class ContentGenerationInDB(BaseModel):
    id: int
    user_id: int
    prompt: str
    generated_text: Dict[str, str]
    image_path: Optional[str]
    include_news: bool
    platforms: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class SocialMediaPostCreate(BaseModel):
    content_generation_id: int
    platform: str
    post_text: str
    image_path: Optional[str] = None
    status: str = "pending"

class SocialMediaPostUpdate(BaseModel):
    status: Optional[str] = None
    error_message: Optional[str] = None
    platform_response: Optional[Dict] = None

class SocialMediaPostInDB(BaseModel):
    id: int
    content_generation_id: int
    platform: str
    post_text: str
    image_path: Optional[str]
    posted_at: Optional[datetime]
    status: str
    error_message: Optional[str]
    platform_response: Optional[Dict]
    created_at: datetime

    class Config:
        from_attributes = True

class UserPreferencesCreate(BaseModel):
    user_id: int
    default_platforms: List[str] = ["twitter", "linkedin"]
    include_news_by_default: bool = True
    auto_post: bool = False
    content_style: str = "professional"
    hashtag_count: int = 15

class UserPreferencesUpdate(BaseModel):
    default_platforms: Optional[List[str]] = None
    include_news_by_default: Optional[bool] = None
    auto_post: Optional[bool] = None
    content_style: Optional[str] = None
    hashtag_count: Optional[int] = None

class UserPreferencesInDB(BaseModel):
    id: int
    user_id: int
    default_platforms: List[str]
    include_news_by_default: bool
    auto_post: bool
    content_style: str
    hashtag_count: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True