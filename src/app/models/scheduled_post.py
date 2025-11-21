from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from ..core.db.database import Base

if TYPE_CHECKING:
    from .post import Post


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, init=False)
    post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("post.id"), nullable=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    platforms: Mapped[str] = mapped_column(String(255), nullable=False)  # Comma-separated list of platforms
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    post: Mapped["Post"] = relationship("Post", back_populates="scheduled_posts", init=False)
    status: Mapped[str] = mapped_column(String(50), default="scheduled")  # scheduled, executing, completed, failed
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)