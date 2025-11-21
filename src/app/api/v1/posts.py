from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Request, Query
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ...api.dependencies import get_current_superuser, get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import ForbiddenException, NotFoundException
from ...core.utils.cache import cache
from ...crud.crud_posts import crud_posts
from ...crud.crud_users import crud_users
from ...schemas.post import PostCreate, PostCreateInternal, PostRead, PostUpdate
from ...schemas.user import UserRead
from ...core.scheduler import Scheduler
from pydantic import BaseModel
from datetime import datetime
from ...models.scheduled_post import ScheduledPost
from ...models.post import Post
from ...models.project import Project

scheduler = Scheduler()

router = APIRouter(tags=["posts"])

@router.get("/test")
async def test_endpoint():
    return {"message": "Posts router is working"}


@router.post("/{username}/post", response_model=PostRead, status_code=201)
async def write_post(
    request: Request,
    username_or_email: str,
    post: PostCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> PostRead:
    db_user = await crud_users.get(db=db, username=username_or_email, is_deleted=False, schema_to_select=UserRead)
    if db_user is None:
        raise NotFoundException("User not found")

    db_user = cast(UserRead, db_user)
    if current_user["id"] != db_user.id:
        raise ForbiddenException()

    post_internal_dict = post.model_dump()
    post_internal_dict["created_by_user_id"] = db_user.id

    post_internal = PostCreateInternal(**post_internal_dict)
    created_post = await crud_posts.create(db=db, object=post_internal)

    post_read = await crud_posts.get(db=db, id=created_post.id, schema_to_select=PostRead)
    if post_read is None:
        raise NotFoundException("Created post not found")

    return cast(PostRead, post_read)


@router.get("/{username}/posts", response_model=PaginatedListResponse[PostRead])
async def read_posts(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
) -> dict:
    db_user = await crud_users.get(db=db, username=username, is_deleted=False, schema_to_select=UserRead)
    if not db_user:
        raise NotFoundException("User not found")

    db_user = cast(UserRead, db_user)
    posts_data = await crud_posts.get_multi(
        db=db,
        offset=compute_offset(page, items_per_page),
        limit=items_per_page,
        created_by_user_id=db_user["id"] if isinstance(db_user, dict) else db_user.id,
        is_deleted=False,
    )

    response: dict[str, Any] = paginated_response(crud_data=posts_data, page=page, items_per_page=items_per_page)
    return response


@router.get("/{username}/post/{id}", response_model=PostRead)
async def read_post(
    request: Request, username: str, id: int, db: Annotated[AsyncSession, Depends(async_get_db)]
) -> PostRead:
    db_user = await crud_users.get(db=db, username=username, is_deleted=False, schema_to_select=UserRead)
    if db_user is None:
        raise NotFoundException("User not found")

    db_user = cast(UserRead, db_user)
    db_post = await crud_posts.get(
        db=db, id=id, created_by_user_id=db_user.id, is_deleted=False, schema_to_select=PostRead
    )
    if db_post is None:
        raise NotFoundException("Post not found")

    return cast(PostRead, db_post)


@router.patch("/{username}/post/{id}")
async def patch_post(
    request: Request,
    username: str,
    id: int,
    values: PostUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    db_user = await crud_users.get(db=db, username=username, is_deleted=False, schema_to_select=UserRead)
    if db_user is None:
        raise NotFoundException("User not found")

    db_user = cast(UserRead, db_user)
    if current_user["id"] != db_user.id:
        raise ForbiddenException()

    db_post = await crud_posts.get(db=db, id=id, is_deleted=False, schema_to_select=PostRead)
    if db_post is None:
        raise NotFoundException("Post not found")

    await crud_posts.update(db=db, object=values, id=id)
    return {"message": "Post updated"}


@router.delete("/{username}/post/{id}")
async def erase_post(
    request: Request,
    username: str,
    id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    db_user = await crud_users.get(db=db, username=username, is_deleted=False, schema_to_select=UserRead)
    if db_user is None:
        raise NotFoundException("User not found")

    db_user = cast(UserRead, db_user)
    if current_user["id"] != db_user.id:
        raise ForbiddenException()

    db_post = await crud_posts.get(db=db, id=id, is_deleted=False, schema_to_select=PostRead)
    if db_post is None:
        raise NotFoundException("Post not found")

    await crud_posts.delete(db=db, id=id)

    return {"message": "Post deleted"}


@router.delete("/{username}/db_post/{id}", dependencies=[Depends(get_current_superuser)])
async def erase_db_post(
    request: Request, username: str, id: int, db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict[str, str]:
    db_user = await crud_users.get(db=db, username=username, is_deleted=False, schema_to_select=UserRead)
    if db_user is None:
        raise NotFoundException("User not found")

    db_post = await crud_posts.get(db=db, id=id, is_deleted=False, schema_to_select=PostRead)
    if db_post is None:
        raise NotFoundException("Post not found")

    await crud_posts.db_delete(db=db, id=id)
    return {"message": "Post deleted from the database"}


class SchedulePostRequest(BaseModel):
    post_id: int
    platforms: list[str]
    scheduled_time: datetime

@router.post("/schedule_post", status_code=202)
async def schedule_post_endpoint(
    request: Request,
    body: SchedulePostRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
):
    """
    Schedule a post for future execution. The post will be picked up and published by the internal background scheduler.
    """
    result = await scheduler.schedule_post(body.post_id, body.platforms, body.scheduled_time, db)
    return result

@router.post("/execute_scheduled_post/{post_id}", status_code=200)
async def execute_scheduled_post_endpoint(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    platforms: str = Query("", description="Comma-separated platforms"),
):
    """
    Manually trigger execution of a scheduled post. This is intended for admin/debugging purposes.
    """
    platform_list = platforms.split(',') if platforms else []
    result = await scheduler.execute_scheduled_post(post_id, platform_list, db)
    return result

@router.post("/execute_next_scheduled_post", status_code=200)
async def execute_next_scheduled_post(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    platforms: str = Query("twitter,instagram,facebook,linkedin,discord", description="Comma-separated platforms"),
):
    platform_list = [p.strip() for p in platforms.split(',') if p.strip()]
    # Find the next unposted post (not deleted, not posted)
    result = await db.execute(
        select(Post).where(Post.is_deleted == False).order_by(Post.created_at.asc())
    )
    posts = result.scalars().all()
    next_post = None
    for post in posts:
        # Assume a post is 'unposted' if it has not been scheduled or posted (customize as needed)
        if not hasattr(post, 'posted_at') or getattr(post, 'posted_at', None) is None:
            next_post = post
            break
    if not next_post:
        return {"status": "no_unposted_post", "message": "No unposted post found."}
    # Post to each platform (stub: replace with actual posting logic)
    results = {}
    for platform in platform_list:
        # Here you would call your social media posting logic
        results[platform] = f"Posted to {platform}"  # Stub
    # Mark as posted (add posted_at field if not present)
    if not hasattr(next_post, 'posted_at'):
        setattr(next_post, 'posted_at', datetime.utcnow())
        await db.commit()
        return {
            "status": "success",
            "post_id": next_post.id,
        "platforms": platform_list,
        "results": results,
        "posted_at": str(getattr(next_post, "posted_at", None))
    }

@router.get("/scheduled_posts")
async def get_all_scheduled_posts(
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(5, ge=1, le=100)
):
    from sqlalchemy import func
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get total count
    count_result = await db.execute(
        select(func.count())
        .select_from(ScheduledPost)
        .join(Project, ScheduledPost.project_id == Project.id)
        .where(Project.created_by_user_id == current_user["id"])
    )
    total = count_result.scalar()
    
    # Get paginated results
    result = await db.execute(
        select(ScheduledPost, Project)
        .join(Project, ScheduledPost.project_id == Project.id)
        .where(Project.created_by_user_id == current_user["id"])
        .order_by(ScheduledPost.scheduled_time.desc())
        .offset(offset)
        .limit(per_page)
    )
    scheduled_posts = result.all()
    
    return {
        "items": [
            {
                "id": s.id,
                "post_id": s.post_id,
                "platforms": s.platforms,
                "scheduled_time": s.scheduled_time.isoformat(),
                "status": s.status,
                "executed_at": s.executed_at.isoformat() if s.executed_at else None,
                "error_message": s.error_message,
                "project_name": p.name if p else None,
            } for s, p in scheduled_posts
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }
