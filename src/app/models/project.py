from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.db.database import Base
from .content import ContentGeneration

if TYPE_CHECKING:
    from .notification import Notification
    from .analytics import PostAnalytics, ABTest, AnalyticsReport, AnalyticsTrend, AnalyticsInsight
    from .content import SocialMediaPost

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True, init=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    social_medias: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    credentials: Mapped[List["SocialMediaCredential"]] = relationship(
        "SocialMediaCredential",
        back_populates="project",
        cascade="all, delete-orphan",
        init=False
    )
    content_generations: Mapped[list["ContentGeneration"]] = relationship(
        "ContentGeneration",
        cascade="all, delete-orphan",
        passive_deletes=True,
        init=False
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="project",
        cascade="all, delete-orphan",
        init=False
    )
    # Analytics relationships
    post_analytics: Mapped[list] = relationship("PostAnalytics", back_populates="project", cascade="all, delete-orphan", init=False)
    ab_tests: Mapped[list] = relationship("ABTest", back_populates="project", cascade="all, delete-orphan", init=False)
    analytics_reports: Mapped[list] = relationship("AnalyticsReport", back_populates="project", cascade="all, delete-orphan", init=False)
    analytics_trends: Mapped[list] = relationship("AnalyticsTrend", back_populates="project", cascade="all, delete-orphan", init=False)
    analytics_insights: Mapped[list] = relationship("AnalyticsInsight", back_populates="project", cascade="all, delete-orphan", init=False)
    social_media_posts: Mapped[list] = relationship("SocialMediaPost", back_populates="project", cascade="all, delete-orphan", init=False)
    with_image: Mapped[bool] = mapped_column(Boolean, default=False)
    image_path: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    status: Mapped[str] = mapped_column(String(50), default="Pending")

    

class SocialMediaCredential(Base):
    __tablename__ = "social_media_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True, init=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)

    # Instagram
    ig_username: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ig_password: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Facebook
    fb_page_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fb_page_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # X (Twitter)
    twitter_api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    twitter_api_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    twitter_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    twitter_access_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # LinkedIn
    linkedin_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linkedin_author_urn: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Discord
    discord_webhook_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Telegram
    telegram_bot_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project: Mapped[Project] = relationship(
        "Project",
        back_populates="credentials",
        init=False
    )
