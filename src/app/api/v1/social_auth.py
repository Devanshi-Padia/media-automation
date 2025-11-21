from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.db.database import async_get_db
from ...models.social_credentials import SocialCredential
from ...models.user import User
from datetime import datetime, timedelta
import requests
import os

router = APIRouter()

FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")
FACEBOOK_REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI")

@router.get("/auth/facebook/callback")
async def facebook_callback(
    request: Request,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends()
):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    # Exchange code for access token
    token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
    params = {
        "client_id": FACEBOOK_CLIENT_ID,
        "redirect_uri": FACEBOOK_REDIRECT_URI,
        "client_secret": FACEBOOK_CLIENT_SECRET,
        "code": code,
    }
    resp = requests.get(token_url, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get access token")
    data = resp.json()
    access_token = data["access_token"]
    expires_in = data.get("expires_in", 60 * 60 * 2)  # Default 2 hours
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    # Store credential
    result = await db.execute(
        SocialCredential.__table__.select().where(
            SocialCredential.user_id == current_user.id,
            SocialCredential.platform == "facebook"
        )
    )
    cred = result.scalars().first()
    if not cred:
        cred = SocialCredential()
        setattr(cred, 'user_id', current_user.id)
        setattr(cred, 'platform', 'facebook')
        setattr(cred, 'access_token', access_token)
        setattr(cred, 'expires_at', expires_at)
        setattr(cred, 'client_id', FACEBOOK_CLIENT_ID)
        setattr(cred, 'client_secret', FACEBOOK_CLIENT_SECRET)
        db.add(cred)
    else:
        setattr(cred, 'access_token', access_token)
        setattr(cred, 'expires_at', expires_at)
        db.add(cred)
    await db.commit()
    return {"status": "connected"}
