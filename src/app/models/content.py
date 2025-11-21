from sqlalchemy import Text, DateTime, Boolean, JSON, ForeignKey, Column, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from ..core.db.database import Base
from typing import Optional, TYPE_CHECKING
from datetime import UTC, datetime

if TYPE_CHECKING:
    from .user import User
    from .project import Project

class ContentGeneration(Base):
    __tablename__ = "content_generations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    prompt: Mapped[str] = mapped_column(Text)
    generated_text: Mapped[dict] = mapped_column(JSON)
    image_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    include_news: Mapped[bool] = mapped_column(Boolean, default=False)
    # The 'platforms' field is redundant as it's stored in the Project model.
    # platforms: Mapped[List[str]] = mapped_column(JSON) 

    user: Mapped["User"] = relationship("User", back_populates="content_generations", init=False)
    social_media_posts: Mapped[list["SocialMediaPost"]] = relationship("SocialMediaPost", back_populates="content_generation", init=False)

    def __repr__(self) -> str:
        return f"ContentGeneration(id={self.id}, prompt={self.prompt})"

class SocialMediaPost(Base):
    """Enhanced social media post tracking with real platform IDs"""
    __tablename__ = "social_media_posts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, init=False)
    content_generation_id: Mapped[int] = mapped_column(Integer, ForeignKey("content_generations.id"), nullable=False)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # twitter, facebook, instagram, etc.
    
    # Actual platform post data
    platform_post_id: Mapped[str] = mapped_column(String(200), nullable=True)  # Real post ID from platform
    post_url: Mapped[str] = mapped_column(String(500), nullable=True)
    post_text: Mapped[str] = mapped_column(Text, nullable=False)
    image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    platform_response: Mapped[dict] = mapped_column(JSON, nullable=True)  # Store full platform response
    
    # Post status
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, posted, failed, deleted
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    content_generation: Mapped["ContentGeneration"] = relationship("ContentGeneration", back_populates="social_media_posts")
    project: Mapped["Project"] = relationship("Project", back_populates="social_media_posts")

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    default_platforms = Column(JSON, default=["twitter", "linkedin"])  # Default platforms to post to
    include_news_by_default = Column(Boolean, default=True)
    auto_post = Column(Boolean, default=False)  # Auto-post after generation
    content_style = Column(String, default="professional")  # professional, casual, technical
    hashtag_count = Column(Integer, default=15)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")