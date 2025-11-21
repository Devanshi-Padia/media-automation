from collections.abc import AsyncGenerator, Callable
from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from typing import Any

import fastapi
from fastapi import APIRouter, Depends, FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from ..api.dependencies import get_current_superuser
from ..core.utils.rate_limit import rate_limiter
from ..middleware.client_cache_middleware import ClientCacheMiddleware
from ..models import *  # noqa: F403
from .config import (
    AppSettings,
    ClientSideCacheSettings,
    EnvironmentOption,
    EnvironmentSettings,
    settings,
)
from .db.database import Base
from .db.database import async_engine as engine


# -------------------- DATABASE --------------------
async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# -------------------- REDIS DISABLED FOR RENDER --------------------
async def create_redis_cache_pool() -> None:
    return  # Disabled


async def close_redis_cache_pool() -> None:
    return  # Disabled


async def create_redis_rate_limit_pool() -> None:
    return  # Disabled


async def close_redis_rate_limit_pool() -> None:
    return  # Disabled


# -------------------- THREADPOOL --------------------
import anyio

async def set_threadpool_tokens(number_of_tokens: int = 100) -> None:
    from anyio import to_thread
    to_thread.current_default_thread_limiter().total_tokens = number_of_tokens


# -------------------- LIFESPAN FACTORY --------------------
def lifespan_factory(
    settings: Any,
    create_tables_on_start: bool = True,
) -> Callable[[FastAPI], _AsyncGeneratorContextManager[Any]]:

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator:
        await set_threadpool_tokens()

        # Create DB tables once
        if create_tables_on_start:
            await create_tables()

        yield  # <-- important

    return lifespan


# -------------------- APPLICATION CREATOR --------------------
def create_application(
    router: APIRouter,
    settings: Any,
    create_tables_on_start: bool = True,
    lifespan: Callable[[FastAPI], _AsyncGeneratorContextManager[Any]] | None = None,
    **kwargs: Any,
) -> FastAPI:

    # Apply App settings (title, description...)
    if isinstance(settings, AppSettings):
        kwargs.update({
            "title": settings.APP_NAME,
            "description": settings.APP_DESCRIPTION,
            "contact": {"name": settings.CONTACT_NAME, "email": settings.CONTACT_EMAIL},
            "license_info": {"name": settings.LICENSE_NAME},
        })

    # Disable docs in production
    if isinstance(settings, EnvironmentSettings):
        kwargs.update({"docs_url": None, "redoc_url": None, "openapi_url": None})

    # Lifespan
    if lifespan is None:
        lifespan = lifespan_factory(settings, create_tables_on_start=create_tables_on_start)

    application = FastAPI(lifespan=lifespan, **kwargs)
    application.include_router(router)

    # Client cache middleware
    if isinstance(settings, ClientSideCacheSettings):
        application.add_middleware(
            ClientCacheMiddleware,
            max_age=settings.CLIENT_CACHE_MAX_AGE
        )  

    # Docs (non-production)
    if isinstance(settings, EnvironmentSettings):
        if settings.ENVIRONMENT != EnvironmentOption.PRODUCTION:
            docs_router = APIRouter()

            if settings.ENVIRONMENT != EnvironmentOption.LOCAL:
                docs_router = APIRouter(dependencies=[Depends(get_current_superuser)])

            @docs_router.get("/docs", include_in_schema=False)
            async def get_swagger_documentation():
                return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")

            @docs_router.get("/redoc", include_in_schema=False)
            async def get_redoc_documentation():
                return get_redoc_html(openapi_url="/openapi.json", title="docs")

            @docs_router.get("/openapi.json", include_in_schema=False)
            async def openapi():
                return get_openapi(
                    title=application.title,
                    version=application.version,
                    routes=application.routes
                )

            application.include_router(docs_router)

    return application
