from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from datetime import datetime

from ...core.db.database import async_get_db
from ...models.notification import Notification
from ...models.user import User
from ...api.dependencies import get_current_user
from ...schemas.notification import NotificationCreate, NotificationResponse, NotificationUpdate

router = APIRouter()


@router.get("/notifications", response_model=List[NotificationResponse])
async def get_user_notifications(
    limit: int = 10,
    offset: int = 0,
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Get notifications for the current user."""
    query = select(Notification).where(
        Notification.user_id == current_user["id"]
    ).order_by(Notification.created_at.desc())
    
    if unread_only:
        query = query.where(Notification.is_read == False)
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    return [
        NotificationResponse(
            id=notification.id,
            title=notification.title,
            message=notification.message,
            notification_type=notification.notification_type,
            is_read=notification.is_read,
            project_id=notification.project_id,
            created_at=notification.created_at,
            updated_at=notification.updated_at
        )
        for notification in notifications
    ]


@router.get("/notifications/unread-count")
async def get_unread_count(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Get count of unread notifications for the current user."""
    query = select(Notification).where(
        Notification.user_id == current_user["id"],
        Notification.is_read == False
    )
    
    result = await db.execute(query)
    unread_notifications = result.scalars().all()
    
    return {"unread_count": len(unread_notifications)}


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Mark a notification as read."""
    # First check if notification exists and belongs to user
    query = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user["id"]
    )
    
    result = await db.execute(query)
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    notification.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Notification marked as read"}


@router.put("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Mark all notifications as read for the current user."""
    stmt = update(Notification).where(
        Notification.user_id == current_user["id"],
        Notification.is_read == False
    ).values(
        is_read=True,
        updated_at=datetime.utcnow()
    )
    
    await db.execute(stmt)
    await db.commit()
    
    return {"message": "All notifications marked as read"}


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Delete a notification."""
    query = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user["id"]
    )
    
    result = await db.execute(query)
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    await db.delete(notification)
    await db.commit()
    
    return {"message": "Notification deleted"}


@router.delete("/notifications")
async def delete_all_notifications(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Delete all notifications for the current user."""
    query = select(Notification).where(Notification.user_id == current_user["id"])
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    for notification in notifications:
        await db.delete(notification)
    
    await db.commit()
    
    return {"message": "All notifications deleted"}


# Internal function to create notifications (used by scheduler)
async def create_notification(
    db: AsyncSession,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "info",
    project_id: Optional[int] = None
) -> Notification:
    """Create a new notification."""
    notification = Notification(
        user_id=user_id,
        project_id=project_id,
        title=title,
        message=message,
        notification_type=notification_type,
        is_read=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    
    return notification 