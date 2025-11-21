from fastapi import APIRouter, Header, HTTPException, Depends, Form, Path, Body, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from pydantic import BaseModel
import os
import logging

from ...core.db.database import async_get_db
from ...crud.crud_social_credentials import get_social_credential
from ...models.user import User
from ...models.social_credentials import SocialCredential
from ...models.post import Post
from ...models.project import Project
from sqlalchemy import select, desc, func
from ...core.services.social_media import SocialMediaService
from ...core.scheduler import Scheduler
from typing import List, Dict, Optional, Any
from ...models.scheduled_post import ScheduledPost
from ...api.dependencies import get_current_user

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY")

class ScheduleRequest(BaseModel):
    platforms: List[str]
    scheduled_time: datetime

@router.post("/post-scheduled")
async def post_scheduled(
    x_api_key: str = Header(None),
    db: AsyncSession = Depends(async_get_db)
):
    logging.info("[SCHEDULER] post_scheduled endpoint called")
    if x_api_key != SECRET_KEY:
        logging.warning("[SCHEDULER] Invalid SECRET_KEY provided")
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await db.execute(
        Post.__table__.select().where(
            Post.scheduled_time <= datetime.utcnow(),
            Post.posted == False
        )
    )
    scheduled_posts = result.scalars().all()
    logging.info(f"[SCHEDULER] Found {len(scheduled_posts)} scheduled posts to process")

    sm_service = SocialMediaService()

    for post in scheduled_posts:
        user_id = post.user_id
        social_medias = post.social_medias
        # logging.info(f"[SCHEDULER] Processing post ID {post.id} for user {user_id} on platforms: {social_medias}")
        if not user_id or not social_medias:
            #logging.warning(f"[SCHEDULER] Skipping post ID {post.id} due to missing user_id or social_medias")
            continue

        platforms = social_medias.split(",")
        for platform in platforms:
            platform = platform.strip().lower()
            cred = await db.run_sync(get_social_credential, user_id, platform)
            if not cred:
                #logging.warning(f"[SCHEDULER] No credentials found for user {user_id} on platform {platform}, skipping.")
                continue

            message = post.text or ""
            image_path = post.image or ""

            credentials = {}
            try:
                #logging.info(f"[SCHEDULER] Attempting to post to {platform} for post ID {post.id}")
                if platform == "facebook":
                    credentials = {
                        "fb_page_id": cred.client_id,
                        "fb_page_access_token": cred.access_token,
                    }
                    sm_service.post_to_facebook({"facebook": message}, image_path, credentials)
                elif platform == "twitter":
                    credentials = {
                        "twitter_api_key": cred.client_id,
                        "twitter_api_secret": cred.client_secret,
                        "twitter_access_token": cred.access_token,
                        "twitter_access_secret": cred.refresh_token,
                    }
                    sm_service.post_to_twitter({"twitter": message}, image_path, credentials)
                elif platform == "instagram":
                    credentials = {
                        "ig_username": cred.ig_username,
                        "ig_password": cred.ig_password,
                    }
                    sm_service.post_to_instagram({"instagram": message}, image_path, credentials)
                elif platform == "linkedin":
                    credentials = {
                        "linkedin_access_token": cred.access_token,
                        "linkedin_author_urn": cred.client_id,
                    }
                    sm_service.post_to_linkedin({"linkedin": message}, image_path, credentials)
                elif platform == "discord":
                    credentials = {
                        "discord_webhook_url": cred.access_token,
                    }
                    sm_service.post_to_discord({"discord": message}, image_path, credentials)
                #logging.info(f"[SCHEDULER] Successfully posted to {platform} for post ID {post.id}")
            except Exception as e:
                #logging.error(f"[SCHEDULER] Error posting to {platform} for post ID {post.id}: {e}")
                pass

            post.posted = True
            db.add(post)
            #  logging.info(f"[SCHEDULER] Marked post ID {post.id} as posted")

        await db.commit()
    #logging.info("[SCHEDULER] Committed all changes to the database")
    return {"status": "success"}

@router.post("/projects/{project_id}/schedule")
async def schedule_post_restful(
    project_id: int = Path(...),
    body: dict = Body(...),
    db: AsyncSession = Depends(async_get_db)
):
    # print(f"[DEBUG] schedule_post_restful called for project_id={project_id} with body={body}")
    project = await db.get(Project, project_id)
    if not project:
        # print(f"[DEBUG] Project {project_id} not found")
        raise HTTPException(status_code=404, detail="Project not found")
    platforms = [p.strip() for p in project.social_medias.split(",") if p.strip()]
    scheduled_time = body.get("scheduled_time")
    # print(f"[DEBUG] scheduled_time received: {scheduled_time}")
    if not scheduled_time:
        raise HTTPException(status_code=400, detail="scheduled_time is required")
    from datetime import datetime, timezone
    if isinstance(scheduled_time, str):
        try:
            # Replace 'Z' with '+00:00' to make it ISO 8601 compatible for Python
            dt = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                scheduled_time = dt.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                scheduled_time = dt  # Already naive, treat as UTC
            # print(f"[DEBUG] scheduled_time (stored as UTC naive): {scheduled_time}")
        except Exception:
            # print(f"[DEBUG] Invalid scheduled_time format: {scheduled_time}")
            raise HTTPException(status_code=400, detail="Invalid scheduled_time format. Use ISO 8601.")
    try:
        result = await db.execute(
            select(Post).where(Post.project_id == project_id).order_by(Post.created_at.desc())
        )
        post = result.scalars().first()
        if not post:
            from ...models.content import ContentGeneration
            cg_result = await db.execute(
                select(ContentGeneration).where(ContentGeneration.project_id == project_id)
            )
            content_generation = cg_result.scalars().first()
            if not content_generation:
                # print(f"[DEBUG] No content found for project {project_id}")
                raise HTTPException(status_code=404, detail="No content found for this project")
            from ...core.scheduler import Scheduler
            scheduler = Scheduler()
            # print(f"[DEBUG] Creating scheduled post for project_id={project_id} at {scheduled_time}")
            result = await scheduler.schedule_project_content(
                project=project,
                content_generation=content_generation,
                platforms=platforms,
                scheduled_time=scheduled_time,
                db=db
            )
            # print(f"[DEBUG] Scheduled post created and committed for project_id={project_id}")
            if result.get("status") == "already_scheduled":
                raise HTTPException(status_code=400, detail=result.get("message", "Project already has a scheduled post"))
            return {"status": "scheduled", **result}
        from ...core.scheduler import Scheduler
        scheduler = Scheduler()
        result = await scheduler.schedule_post(post.id, platforms, scheduled_time, db)
        # print(f"[DEBUG] Scheduled post created and committed for post_id={post.id}")
        return {"status": "scheduled", **result}
    except Exception as e:
        # print(f"[DEBUG] Exception in schedule_post_restful: {e}")
        import traceback; traceback.print_exc()
        raise

@router.get("/projects/{project_id}/schedule-status")
async def get_schedule_status(
    project_id: int = Path(...),
    db: AsyncSession = Depends(async_get_db)
):
    """Check if a project already has a scheduled post."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check for existing scheduled posts
    result = await db.execute(
        select(ScheduledPost).where(
            ScheduledPost.project_id == project_id,
            ScheduledPost.status.in_(["scheduled", "executing"])
        )
    )
    existing_scheduled = result.scalar_one_or_none()
    
    if existing_scheduled:
        return {
            "has_scheduled_post": True,
            "scheduled_post_id": existing_scheduled.id,
            "scheduled_time": existing_scheduled.scheduled_time.isoformat() if existing_scheduled.scheduled_time else None,
            "status": existing_scheduled.status
        }
    else:
        return {
            "has_scheduled_post": False,
            "scheduled_post_id": None,
            "scheduled_time": None,
            "status": None
        }

@router.put("/projects/{project_id}/reschedule")
async def reschedule_project(
    project_id: int = Path(...),
    body: dict = Body(...),
    db: AsyncSession = Depends(async_get_db)
):
    """Reschedule an existing scheduled post for a project."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    scheduled_time = body.get("scheduled_time")
    if not scheduled_time:
        raise HTTPException(status_code=400, detail="scheduled_time is required")
    
    # Parse scheduled_time
    from datetime import datetime, timezone
    if isinstance(scheduled_time, str):
        try:
            dt = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                scheduled_time = dt.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                scheduled_time = dt
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid scheduled_time format. Use ISO 8601.")
    
    # Find existing scheduled post
    result = await db.execute(
        select(ScheduledPost).where(
            ScheduledPost.project_id == project_id,
            ScheduledPost.status.in_(["scheduled", "executing"])
        )
    )
    existing_scheduled = result.scalar_one_or_none()
    
    if not existing_scheduled:
        raise HTTPException(status_code=404, detail="No scheduled post found for this project")
    
    # Update the scheduled time
    existing_scheduled.scheduled_time = scheduled_time
    existing_scheduled.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(existing_scheduled)
    
    return {
        "status": "rescheduled",
        "message": f"Project rescheduled for {scheduled_time}",
        "scheduled_post_id": existing_scheduled.id
    }

@router.post("/projects/{project_id}/save-credentials")
async def save_social_credentials(
    project_id: int,
    user_id: int = Form(...),
    # Twitter
    x_api_key: str = Form(None),
    x_api_secret: str = Form(None),
    x_access_token: str = Form(None),
    x_access_secret: str = Form(None),
    # Facebook
    fb_app_id: str = Form(None),
    fb_app_secret: str = Form(None),
    fb_access_token: str = Form(None),
    fb_page_id: str = Form(None),
    fb_page_access_token: str = Form(None),
    # Instagram
    ig_username: str = Form(None),
    ig_password: str = Form(None),
    # LinkedIn
    linkedin_client_id: str = Form(None),
    linkedin_client_secret: str = Form(None),
    linkedin_access_token: str = Form(None),
    # Discord
    discord_client_id: str = Form(None),
    discord_client_secret: str = Form(None),
    discord_bot_token: str = Form(None),
    discord_webhook_url: str = Form(None),
    db: AsyncSession = Depends(async_get_db)
):
    # Twitter
    if x_api_key and x_api_secret and x_access_token and x_access_secret:
        cred = SocialCredential(
            user_id=user_id,
            platform='twitter',
            access_token=x_access_token,
            refresh_token=x_access_secret,
            expires_at=None,
            client_id=x_api_key,
            client_secret=x_api_secret,
            ig_username=None,
            ig_password=None
        )
        db.add(cred)

    # Facebook
    if fb_page_id and fb_page_access_token:
        cred = SocialCredential(
            user_id=user_id,
            platform='facebook',
            access_token=fb_page_access_token,
            refresh_token=None,
            expires_at=None,
            client_id=fb_page_id,
            client_secret=fb_app_secret,
            ig_username=None,
            ig_password=None
        )
        db.add(cred)

    # Instagram
    if ig_username and ig_password:
        cred = SocialCredential(
            user_id=user_id,
            platform='instagram',
            access_token='',
            refresh_token=None,
            expires_at=None,
            client_id=None,
            client_secret=None,
            ig_username=ig_username,
            ig_password=ig_password
        )
        db.add(cred)

    # LinkedIn
    if linkedin_client_id and linkedin_access_token:
        cred = SocialCredential(
            user_id=user_id,
            platform='linkedin',
            access_token=linkedin_access_token,
            refresh_token=None,
            expires_at=None,
            client_id=linkedin_client_id,
            client_secret=linkedin_client_secret,
            ig_username=None,
            ig_password=None
        )
        db.add(cred)

    # Discord
    if discord_webhook_url:
        cred = SocialCredential(
            user_id=user_id,
            platform='discord',
            access_token=discord_webhook_url,
            refresh_token=discord_bot_token,
            expires_at=None,
            client_id=discord_client_id,
            client_secret=discord_client_secret,
            ig_username=None,
            ig_password=None
        )
        db.add(cred)

    await db.commit()
    return {"status": "success"}

@router.post("/projects/{project_id}/posts")
async def create_post(
    project_id: int = Path(...),
    body: dict = Body(...),
    db: AsyncSession = Depends(async_get_db)
):
    # Validate and extract data from the request body
    text = body.get("text")
    image = body.get("image")
    social_medias = body.get("social_medias")
    scheduled_time = body.get("scheduled_time")

    if not text and not image:
        raise HTTPException(status_code=400, detail="Either text or image must be provided")
    if not social_medias:
        raise HTTPException(status_code=400, detail="social_medias field is required")

    # Create a new post instance
    new_post = Post(
        project_id=project_id,
        user_id=1,  # This should be the ID of the user creating the post
        text=text,
        image=image,
        social_medias=social_medias,
        scheduled_time=scheduled_time,
        posted=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)

    return {"status": "success", "post_id": new_post.id}

@router.put("/projects/{project_id}/posts/{post_id}")
async def update_post(
    project_id: int = Path(...),
    post_id: int = Path(...),
    body: dict = Body(...),
    db: AsyncSession = Depends(async_get_db)
):
    # Validate and extract data from the request body
    text = body.get("text")
    image = body.get("image")
    social_medias = body.get("social_medias")
    scheduled_time = body.get("scheduled_time")

    if not text and not image:
        raise HTTPException(status_code=400, detail="Either text or image must be provided")
    post_id = body.get("post_id")
    if not post_id:
        raise HTTPException(status_code=400, detail="post_id is required")
    result = await db.get(Post, post_id)
    if not result:
        raise HTTPException(status_code=404, detail="Post not found")
    post = result

    # Update the post instance
    post.text = text
    post.image = image
    post.social_medias = social_medias
    post.scheduled_time = scheduled_time
    post.updated_at = datetime.utcnow()

    db.add(post)
    await db.commit()
    await db.refresh(post)

    return {"status": "success", "post_id": post.id}

@router.get("/scheduled_posts")
async def get_scheduled_posts(
    db: AsyncSession = Depends(async_get_db),
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    # Only show scheduled posts for the current user
    result = await db.execute(
        select(Project, ScheduledPost)
        .join(ScheduledPost, ScheduledPost.project_id == Project.id)
        .where(Project.created_by_user_id == current_user["id"])
    )
    posts = []
    for project, scheduled_post in result.all():
        posts.append({
            "project_name": project.name,
            "scheduled_time": scheduled_post.scheduled_time.isoformat() if scheduled_post.scheduled_time else None,
            "status": scheduled_post.status,
            "social_medias": project.social_medias
        })
    return posts
