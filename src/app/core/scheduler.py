from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.services.social_media import SocialMediaService
from ..models.post import Post
from ..models.scheduled_post import ScheduledPost
from ..core.db.database import async_get_db
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
import threading
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class Scheduler:
    """Internal scheduler for handling scheduled posts."""
    
    def __init__(self):
        self.social_media_service = SocialMediaService()
    
    async def schedule_post(self, post_id: int, platforms: list[str], run_time: datetime, db: AsyncSession) -> dict:
        try:
            scheduled_post = ScheduledPost(
                post_id=post_id,
                platforms=','.join(platforms),
                scheduled_time=run_time,
                status='scheduled',
                executed_at=None,
                error_message=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(scheduled_post)
            await db.commit()
            await db.refresh(scheduled_post)
            return {
                "status": "success",
                "message": f"Post scheduled for {run_time}",
                "scheduled_post_id": scheduled_post.id
            }
        except Exception as e:
            await db.rollback()
            raise Exception(f"Failed to schedule post: {str(e)}")
    
    async def execute_scheduled_post(self, post_id: int, platforms: list[str], db: AsyncSession) -> dict:
        scheduled_post = None
        try:
            result = await db.execute(select(Post).where(Post.id == post_id, Post.is_deleted == False))
            post = result.scalar_one_or_none()
            if not post:
                raise Exception(f"Post with id {post_id} not found or deleted")
            scheduled_result = await db.execute(
                select(ScheduledPost).where(ScheduledPost.post_id == post_id)
            )
            scheduled_post = scheduled_result.scalar_one_or_none()
            if scheduled_post:
                scheduled_post.status = "executing"
                await db.commit()
            text_dict = {}
            post_text = getattr(post, 'text', None)
            for platform in ['twitter', 'instagram', 'facebook', 'linkedin', 'discord']:
                text_dict[platform] = post_text if post_text is not None else ""
            image_path = getattr(post, 'media_url', "") or ""
            results = {}
            for platform in platforms:
                platform = platform.strip().lower()
                try:
                    if platform == 'twitter':
                        result = self.social_media_service.post_to_twitter(text_dict, image_path)
                        if result is not None and hasattr(result, "__await__"):
                            results[platform] = await result
                        else:
                            results[platform] = result
                    elif platform == 'instagram':
                        method = getattr(self.social_media_service, "post_to_instagram", None)
                        if callable(method):
                            result = method(text_dict, image_path)
                            if asyncio.iscoroutine(result):
                                result = await result
                            results[platform] = result
                    elif platform == 'facebook':
                        result = self.social_media_service.post_to_facebook(text_dict, image_path)
                        results[platform] = result
                    elif platform == 'linkedin':
                        results[platform] = self.social_media_service.post_to_linkedin(text_dict, image_path)
                    elif platform == 'discord':
                        results[platform] = self.social_media_service.post_to_discord(text_dict, image_path)
                    else:
                        results[platform] = None
                        print(f"Unknown platform: {platform}")
                except Exception as e:
                    results[platform] = None
                    print(f"Error posting to {platform}: {e}")
            if scheduled_post:
                scheduled_post.status = "completed"
                scheduled_post.executed_at = datetime.utcnow()
                await db.commit()
            return {
                "post_id": post_id,
                "platforms": platforms,
                "results": results,
                "status": "completed"
            }
        except Exception as e:
            if scheduled_post:
                scheduled_post.status = "failed"
                scheduled_post.error_message = str(e)
                await db.commit()
            raise e
    async def get_pending_scheduled_posts(self, db: AsyncSession):
        stmt = select(ScheduledPost).where(
            ScheduledPost.status == "scheduled",
            ScheduledPost.scheduled_time <= datetime.utcnow()
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def schedule_project_content(
        self,
        project,
        content_generation,
        platforms,
        scheduled_time,
        db
    ):
        from ..models.scheduled_post import ScheduledPost
        from datetime import datetime

        # Check if there's already a scheduled post for this project
        existing_scheduled = await db.scalar(
            select(ScheduledPost).where(
                ScheduledPost.project_id == project.id,
                ScheduledPost.status.in_(["scheduled", "executing"])
            )
        )
        
        if existing_scheduled:
            return {
                "status": "already_scheduled",
                "message": f"Project already has a scheduled post (ID: {existing_scheduled.id})",
                "scheduled_post_id": existing_scheduled.id
            }

        scheduled_post = ScheduledPost(
            post_id=None,  # No post
            project_id=project.id,  # Link to project
            platforms=",".join(platforms),
            scheduled_time=scheduled_time,
            status='scheduled',
            executed_at=None,
            error_message=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(scheduled_post)
        await db.commit()
        await db.refresh(scheduled_post)
        return {
            "status": "scheduled",
            "message": f"Project content scheduled for {scheduled_time}",
            "scheduled_post_id": scheduled_post.id
        }

async def process_due_scheduled_posts_async():
    import asyncio
    from ..models import ScheduledPost, Project, ContentGeneration, SocialMediaCredential, Notification
    from sqlalchemy import select
    from ..core.db.database import async_get_db
    from ..core.services.social_media import SocialMediaService
    from datetime import datetime

    print(f"[APScheduler] Job started at {datetime.now(timezone.utc)}")
    db_gen = async_get_db()
    db = await anext(db_gen)
    try:
        # Find all due scheduled posts that haven't been processed yet
        result = await db.execute(
            select(ScheduledPost).where(
                ScheduledPost.status == "scheduled",
                ScheduledPost.scheduled_time <= datetime.utcnow()
            )
        )
        pending_posts = result.scalars().all()
        print(f"[APScheduler] Found {len(pending_posts)} pending scheduled posts at {datetime.now(timezone.utc)}")
        
        for scheduled_post in pending_posts:
            print(f"[APScheduler] Processing scheduled_post id={scheduled_post.id}, post_id={scheduled_post.post_id}, project_id={getattr(scheduled_post, 'project_id', None)}")
            
            # Double-check status to prevent duplicate processing
            await db.refresh(scheduled_post)
            if scheduled_post.status != "scheduled":
                print(f"[APScheduler] Skipping scheduled_post {scheduled_post.id} - status is {scheduled_post.status}")
                continue
                
            if scheduled_post.post_id:
                print(f"[APScheduler] Skipping post-based scheduled_post {scheduled_post.id} (not supported in this mode)")
                continue
            elif scheduled_post.project_id:
                # Mark as executing to prevent duplicate processing
                scheduled_post.status = "executing"
                await db.commit()
                
                try:
                    project = await db.get(Project, scheduled_post.project_id)
                    content_generation = await db.scalar(
                        select(ContentGeneration).where(ContentGeneration.project_id == scheduled_post.project_id)
                    )
                    creds_result = await db.execute(
                        select(SocialMediaCredential).where(SocialMediaCredential.project_id == scheduled_post.project_id)
                    )
                    all_creds = creds_result.scalars().all()
                    credentials_map = {c.platform: c.__dict__ for c in all_creds}
                    text_payload = content_generation.generated_text if content_generation and content_generation.generated_text else {"default": project.topic}
                    image_path = content_generation.image_path if content_generation and content_generation.image_path else None
                    service = SocialMediaService()
                    results = service.post_to_social_media(text_payload, image_path, credentials_map)
                    print(f"[APScheduler] Processed scheduled project: {project.id}, results: {results}")
                    
                    # Update scheduled post status
                    scheduled_post.status = "completed"
                    scheduled_post.executed_at = datetime.utcnow()
                    
                    # Update project status based on platform results
                    successful_platforms = results.get('successful_platforms', []) if results else []
                    failed_platforms = results.get('failed_platforms', []) if results else []
                    if successful_platforms and failed_platforms:
                        project.status = "Partial"
                    elif successful_platforms:
                        project.status = "Posted"
                    else:
                        project.status = "Failed"
                    
                    # Create notification for project execution
                    notification_type = "success" if successful_platforms and not failed_platforms else "warning" if successful_platforms and failed_platforms else "error"
                    notification_title = f"Project '{project.name}' Execution Complete"
                    
                    if successful_platforms and not failed_platforms:
                        notification_message = f"Your project '{project.name}' was successfully posted to: {', '.join(successful_platforms)}"
                    elif successful_platforms and failed_platforms:
                        notification_message = f"Your project '{project.name}' was partially posted. Success: {', '.join(successful_platforms)}. Failed: {', '.join(failed_platforms)}"
                    else:
                        notification_message = f"Your project '{project.name}' failed to post to any platforms. Please check your credentials and try again."
                    
                    # Create notification
                    notification = Notification(
                        user_id=project.created_by_user_id,
                        project_id=project.id,
                        title=notification_title,
                        message=notification_message,
                        notification_type=notification_type,
                        is_read=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(notification)
                    
                    await db.commit()
                    print(f"[APScheduler] Successfully completed scheduled_post {scheduled_post.id}")
                    
                except Exception as e:
                    print(f"[APScheduler] Error processing scheduled_post {scheduled_post.id}: {e}")
                    scheduled_post.status = "failed"
                    scheduled_post.error_message = str(e)
                    
                    # Create error notification
                    if project:
                        notification = Notification(
                            user_id=project.created_by_user_id,
                            project_id=project.id,
                            title=f"Project '{project.name}' Execution Failed",
                            message=f"Your project '{project.name}' failed to execute due to an error: {str(e)}",
                            notification_type="error",
                            is_read=False,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        db.add(notification)
                    
                    await db.commit()
            else:
                print(f"[APScheduler] Skipping scheduled post with no post_id or project_id: {scheduled_post}")
    except Exception as e:
        print(f"[APScheduler] Exception in job: {e}")
        import traceback; traceback.print_exc()
    finally:
        await db.aclose()

async def sync_analytics_async():
    """Scheduled task to sync analytics data for all projects"""
    try:
        from .services.analytics_sync import AnalyticsSyncService
        
        async with async_get_db() as db:
            sync_service = AnalyticsSyncService()
            result = await sync_service.sync_all_projects_analytics(db)
            print(f"[APScheduler] Analytics sync completed: {result}")
            
    except Exception as e:
        print(f"[APScheduler] Error in analytics sync: {str(e)}")

def schedule_apscheduler_job(app):
    # print("[APScheduler] schedule_apscheduler_job called")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(process_due_scheduled_posts_async, 'interval', minutes=1)
    # Add analytics sync job to run every 6 hours
    scheduler.add_job(sync_analytics_async, 'interval', hours=6)
    scheduler.start()
    app.state.apscheduler = scheduler