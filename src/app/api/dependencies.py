from typing import Annotated, Any, cast

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.db.database import async_get_db
from ..core.exceptions.http_exceptions import ForbiddenException, RateLimitException, UnauthorizedException
from ..core.logger import logging
from ..core.security import TokenType, oauth2_scheme, verify_token
from ..core.utils.rate_limit import rate_limiter
from ..crud.crud_rate_limit import crud_rate_limits
from ..crud.crud_tier import crud_tiers
from ..crud.crud_users import crud_users
from ..schemas.rate_limit import RateLimitRead, sanitize_path
from ..schemas.tier import TierRead

import jwt
from fastapi import Request, HTTPException, Depends
from starlette.status import HTTP_401_UNAUTHORIZED

SECRET_KEY = settings.SECRET_KEY.get_secret_value()

async def get_current_user(request: Request, db: AsyncSession = Depends(async_get_db)):
    print("[DEBUG] get_current_user called")
    token: str | None = None
    
    # Try to get token from Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    # If no header, fall back to cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Not authenticated: No token provided")
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        # Fetch user from DB
        db_user = await crud_users.get(db=db, username=username)
        if not db_user:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="User not found")
        # If db_user is a model, convert to dict with proper field extraction
        if hasattr(db_user, "id"):
            user_dict = {
                "id": db_user.id,
                "username": db_user.username,
                "email": db_user.email,
                "name": db_user.name,
                "is_superuser": db_user.is_superuser,
                "is_deleted": db_user.is_deleted,
                "is_email_verified": db_user.is_email_verified,
                "tier_id": db_user.tier_id,
                "created_at": db_user.created_at,
                "updated_at": db_user.updated_at,
                "deleted_at": db_user.deleted_at,
                "uuid": db_user.uuid
            }
            print(f"[DEBUG] get_current_user - User {user_dict['username']} is_superuser: {user_dict['is_superuser']}")
        else:
            user_dict = db_user
        return user_dict
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_optional_user(request: Request, db: AsyncSession = Depends(async_get_db)) -> dict | None:
    token: str | None = None
    
    # Try to get token from Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    # If no header, fall back to cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        return None
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if not username:
            return None
        # Fetch user from DB
        db_user = await crud_users.get(db=db, username=username)
        if not db_user:
            return None
        # If db_user is a model, convert to dict with proper field extraction
        if hasattr(db_user, "id"):
            user_dict = {
                "id": db_user.id,
                "username": db_user.username,
                "email": db_user.email,
                "name": db_user.name,
                "is_superuser": db_user.is_superuser,
                "is_deleted": db_user.is_deleted,
                "is_email_verified": db_user.is_email_verified,
                "tier_id": db_user.tier_id,
                "created_at": db_user.created_at,
                "updated_at": db_user.updated_at,
                "deleted_at": db_user.deleted_at,
                "uuid": db_user.uuid
            }
        else:
            user_dict = db_user
        return user_dict
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception as exc:
        logging.error(f"Unexpected error in get_optional_user: {exc}")
        return None


async def get_current_superuser(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if not current_user["is_superuser"]:
        raise ForbiddenException("You do not have enough privileges.")

    return current_user


async def rate_limiter_dependency(
    request: Request, db: Annotated[AsyncSession, Depends(async_get_db)], user: dict | None = Depends(get_optional_user)
) -> None:
    if hasattr(request.app.state, "initialization_complete"):
        await request.app.state.initialization_complete.wait()

    path = sanitize_path(request.url.path)
    if user:
        user_id = user["id"]
        tier = await crud_tiers.get(db, id=user["tier_id"], schema_to_select=TierRead)
        if tier:
            tier = cast(TierRead, tier)
            rate_limit = await crud_rate_limits.get(db=db, tier_id=tier.id, path=path, schema_to_select=RateLimitRead)
            if rate_limit:
                rate_limit = cast(RateLimitRead, rate_limit)
                limit, period = rate_limit.limit, rate_limit.period
            else:
                import logging
                logging.warning(
                    f"User {user_id} with tier '{tier.name}' has no specific rate limit for path '{path}'. "
                    "Applying default rate limit."
                )
                from app.core.config import DEFAULT_LIMIT, DEFAULT_PERIOD
                limit, period = DEFAULT_LIMIT, DEFAULT_PERIOD
        else:
            import logging
            logging.warning(f"User {user_id} has no assigned tier. Applying default rate limit.")
            from app.core.config import DEFAULT_LIMIT, DEFAULT_PERIOD
            limit, period = DEFAULT_LIMIT, DEFAULT_PERIOD

    is_limited = await rate_limiter.is_rate_limited(db=db, user_id=user_id, path=path, limit=limit, period=period)
    if is_limited:
        raise RateLimitException("Rate limit exceeded.")
