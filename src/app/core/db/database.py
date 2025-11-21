from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from ..config import settings


class Base(MappedAsDataclass, DeclarativeBase, kw_only=True):
    pass


# ------ USE POSTGRES_URL DIRECTLY ------
# Render uses POSTGRES_URL (not POSTGRES_URI)
DATABASE_URL = settings.POSTGRES_URL

# Async engine
async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)

# Session maker
local_session = async_sessionmaker(
    bind=async_engine, 
    class_=AsyncSession,
    expire_on_commit=False
)


async def async_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with local_session() as db:
        yield db
