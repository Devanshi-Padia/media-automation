from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from ..config import settings
import urllib.parse

class Base(MappedAsDataclass, DeclarativeBase, kw_only=True):
    pass

# Fix Render Postgres URL for asyncpg
raw_url = settings.POSTGRES_URL or settings.DATABASE_URL

# Ensure asyncpg prefix
if raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://")

# Remove sslmode if SQLAlchemy added it
parsed = urllib.parse.urlparse(raw_url)
query = urllib.parse.parse_qs(parsed.query)

# asyncpg expects ssl=true

if "sslmode" in query:
    query.pop("sslmode")
if "ssl" in query:
    query.pop("ssl")

# ADD correct asyncpg SSL
query["ssl"] = ["require"]


clean_query = urllib.parse.urlencode(query, doseq=True)

DATABASE_URL = urllib.parse.urlunparse(
    parsed._replace(query=clean_query)
)

async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

local_session = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def async_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with local_session() as db:
        yield db
