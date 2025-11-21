import os
from enum import Enum

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# -----------------------------------------------------------
# Base class – reads both Render environment variables AND .env locally
# -----------------------------------------------------------
class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",                 # used only locally
        env_file_encoding="utf-8",
        extra="ignore"
    )


# -----------------------------------------------------------
# App Info
# -----------------------------------------------------------
class AppSettings(BaseConfig):
    APP_NAME: str = "FastAPI app"
    APP_DESCRIPTION: str | None = None
    APP_VERSION: str | None = None
    LICENSE_NAME: str | None = None
    CONTACT_NAME: str | None = None
    CONTACT_EMAIL: str | None = None


# -----------------------------------------------------------
# Cryptography / JWT
# -----------------------------------------------------------
class CryptSettings(BaseConfig):
    SECRET_KEY: SecretStr = SecretStr("secret")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


# -----------------------------------------------------------
# POSTGRES CONFIG (Render-ready)
# -----------------------------------------------------------
class PostgresSettings(BaseConfig):
    POSTGRES_URL: str | None = None  # Render will set this
    POSTGRES_ASYNC_PREFIX: str = "postgresql+asyncpg://"

    # Local DEV (optional values)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "postgres"

    @property
    def DATABASE_URL(self) -> str:
        # If Render provided full URL
        if self.POSTGRES_URL:
            url = self.POSTGRES_URL
            # Ensure SSL required for Render
            if "sslmode" not in url:
                url += "?sslmode=require"
            return url

        # Local fallback
        return (
            f"{self.POSTGRES_ASYNC_PREFIX}"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )


# -----------------------------------------------------------
# First Admin User
# -----------------------------------------------------------
class FirstUserSettings(BaseConfig):
    ADMIN_NAME: str = "veda"
    ADMIN_EMAIL: str = "admin@admin.com"
    ADMIN_USERNAME: str = "veda"
    ADMIN_PASSWORD: str = "ved@1234"


# -----------------------------------------------------------
# Social API Keys
# -----------------------------------------------------------
class ContentGenerationSettings(BaseConfig):
    OPENAI_API_KEY: str = ""
    NEWS_API_KEY: str = ""

    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_ACCESS_TOKEN: str = ""
    TWITTER_ACCESS_SECRET: str = ""

    IG_USERNAME: str = ""
    IG_PASSWORD: str = ""

    LINKEDIN_ACCESS_TOKEN: str = ""

    FB_PAGE_ID: str = ""
    FB_PAGE_ACCESS_TOKEN: str = ""

    DISCORD_WEBHOOK_URL: str = ""


# -----------------------------------------------------------
# Redis Cache
# -----------------------------------------------------------
class RedisCacheSettings(BaseConfig):
    REDIS_CACHE_HOST: str = "localhost"
    REDIS_CACHE_PORT: int = 6379
    REDIS_CACHE_URL: str = ""


# -----------------------------------------------------------
# Client caching
# -----------------------------------------------------------
class ClientSideCacheSettings(BaseConfig):
    CLIENT_CACHE_MAX_AGE: int = 60


# -----------------------------------------------------------
# Redis Queue
# -----------------------------------------------------------
class RedisQueueSettings(BaseConfig):
    REDIS_QUEUE_HOST: str = "localhost"
    REDIS_QUEUE_PORT: int = 6379


# -----------------------------------------------------------
# Rate Limiting
# -----------------------------------------------------------
class RedisRateLimiterSettings(BaseConfig):
    REDIS_RATE_LIMIT_HOST: str = "localhost"
    REDIS_RATE_LIMIT_PORT: int = 6379
    REDIS_RATE_LIMIT_URL: str = ""


class DefaultRateLimitSettings(BaseConfig):
    DEFAULT_RATE_LIMIT_LIMIT: int = 10
    DEFAULT_RATE_LIMIT_PERIOD: int = 3600


# -----------------------------------------------------------
# Admin Panel Settings
# -----------------------------------------------------------
class CRUDAdminSettings(BaseConfig):
    CRUD_ADMIN_ENABLED: bool = True
    CRUD_ADMIN_MOUNT_PATH: str = "/admin"

    CRUD_ADMIN_ALLOWED_IPS_LIST: list[str] | None = None
    CRUD_ADMIN_ALLOWED_NETWORKS_LIST: list[str] | None = None
    CRUD_ADMIN_MAX_SESSIONS: int = 10
    CRUD_ADMIN_SESSION_TIMEOUT: int = 1440
    SESSION_SECURE_COOKIES: bool = True

    CRUD_ADMIN_TRACK_EVENTS: bool = True
    CRUD_ADMIN_TRACK_SESSIONS: bool = True

    CRUD_ADMIN_REDIS_ENABLED: bool = False
    CRUD_ADMIN_REDIS_HOST: str = "localhost"
    CRUD_ADMIN_REDIS_PORT: int = 6379
    CRUD_ADMIN_REDIS_DB: int = 0
    CRUD_ADMIN_REDIS_PASSWORD: str | None = None
    CRUD_ADMIN_REDIS_SSL: bool = False


# -----------------------------------------------------------
# Environment (local / staging / production)
# -----------------------------------------------------------
class EnvironmentOption(Enum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentSettings(BaseConfig):
    ENVIRONMENT: EnvironmentOption = EnvironmentOption.LOCAL


# -----------------------------------------------------------
# Combined Settings
# -----------------------------------------------------------
class Settings(
    AppSettings,
    PostgresSettings,
    CryptSettings,
    FirstUserSettings,
    ContentGenerationSettings,
    RedisCacheSettings,
    ClientSideCacheSettings,
    RedisQueueSettings,
    RedisRateLimiterSettings,
    DefaultRateLimitSettings,
    CRUDAdminSettings,
    EnvironmentSettings,
):
    pass


settings = Settings()

DEFAULT_LIMIT = 100
DEFAULT_PERIOD = 60
