import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, JSON, Column, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base

class Post(Base):
    __tablename__ = "post"
    scheduled_posts: Mapped[list] = relationship("ScheduledPost", back_populates="post")
    analytics: Mapped[list] = relationship("PostAnalytics", back_populates="post")
    id: Mapped[int] = mapped_column("id", autoincrement=True, nullable=False, unique=True, primary_key=True, init=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(30))
    texts: Mapped[dict] = mapped_column(JSON)  # Store all platform texts as JSON
    images: Mapped[dict] = mapped_column(JSON)  # Store per-platform images as JSON
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    social_medias: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(String)
    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    image: Mapped[str] = mapped_column(String)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(default_factory=uuid_pkg.uuid4, primary_key=True, unique=True)
    # All fields below have defaults
    media_url: Mapped[str | None] = mapped_column(String, default=None)
    platform_post_ids: Mapped[dict] = mapped_column(JSON, default=dict)  # Store platform-specific post IDs
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    posted: Mapped[bool] = mapped_column(Boolean, default=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
