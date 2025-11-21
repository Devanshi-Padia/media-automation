import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .social_credentials import SocialCredential
from ..core.db.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .content import ContentGeneration, UserPreferences
    from .notification import Notification

class User(Base):
    __tablename__ = "users"

    # 1. Fields WITHOUT defaults
    id: Mapped[int] = mapped_column("id", autoincrement=True, nullable=False, unique=True, primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(30))
    username: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)

    # 2. Fields WITH defaults (including default_factory)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(default_factory=uuid_pkg.uuid4, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    profile_image_url: Mapped[str] = mapped_column(String, default="https://profileimageurl.com")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    tier_id: Mapped[int | None] = mapped_column(ForeignKey("tier.id"), index=True, default=None, init=False)

    # 3. Relationships (must be last, with defaults)
    content_generations: Mapped[list["ContentGeneration"]] = relationship("ContentGeneration", back_populates="user")
    preferences: Mapped["UserPreferences"] = relationship("UserPreferences", back_populates="user", uselist=False, default=None)
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user")
    social_credentials: Mapped[list["SocialCredential"]] = relationship("SocialCredential", back_populates="user")
    analytics_reports: Mapped[list] = relationship("AnalyticsReport", back_populates="user")
