from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from ..core.db.database import Base

if TYPE_CHECKING:
    from .user import User

class SocialCredential(Base):
    __tablename__ = "social_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    platform: Mapped[str] = mapped_column(nullable=False)  # e.g., 'facebook', 'instagram'
    access_token: Mapped[str] = mapped_column(nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    client_id: Mapped[str | None] = mapped_column(nullable=True)
    client_secret: Mapped[str | None] = mapped_column(nullable=True)
    ig_username: Mapped[str | None] = mapped_column(nullable=True)
    ig_password: Mapped[str | None] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="social_credentials", init=False)
