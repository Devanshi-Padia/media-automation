import asyncio
from datetime import datetime
from src.app.core.db.database import async_get_db
# Import all models to resolve relationships
from src.app.models import user, social_credentials, scheduled_post
from src.app.models.scheduled_post import ScheduledPost
from src.app.models.project import Project
from sqlalchemy import select

async def main():
    db_gen = async_get_db()
    db = await anext(db_gen)
    try:
        # Check all scheduled posts
        result = await db.execute(select(ScheduledPost))
        posts = result.scalars().all()
        print(f"Found {len(posts)} scheduled posts:")
        for post in posts:
            print(f"ID: {post.id}, Status: {post.status}, Scheduled Time: {post.scheduled_time}, Project ID: {getattr(post, 'project_id', None)}")
        
        # Check for completed scheduled posts that haven't updated project status
        completed_posts = await db.execute(
            select(ScheduledPost).where(
                ScheduledPost.status == "completed",
                ScheduledPost.project_id.isnot(None)
            )
        )
        completed_posts = completed_posts.scalars().all()
        
        print(f"\nFound {len(completed_posts)} completed scheduled posts:")
        for post in completed_posts:
            project = await db.get(Project, post.project_id)
            if project:
                print(f"Project: {project.name}, Current Status: {project.status}")
                if project.status == "Pending":
                    project.status = "Posted"
                    db.add(project)
                    print(f"Updated project '{project.name}' status from 'Pending' to 'Posted'")
        
        await db.commit()
        print("\nDatabase updated successfully!")
        
    finally:
        await db.aclose()

if __name__ == "__main__":
    asyncio.run(main())