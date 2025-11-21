from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from ..config import settings


class Base(MappedAsDataclass, DeclarativeBase, kw_only=True):
    pass

# --- FIX START ---
# Use POSTGRES_URL directly from the environment
if settings.POSTGRES_URL:
    DATABASE_URL = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    # Build fallback using individual variables
    DATABASE_URL = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:"
        f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
# --- FIX END ---

async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)

local_session = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


async def async_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with local_session() as db:
        yield db
