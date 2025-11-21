#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.core.db.database import async_get_db
from app.models.scheduled_post import ScheduledPost
from app.models.project import Project
from sqlalchemy import select

async def main():
    db_gen = async_get_db()
    db = await anext(db_gen)
    try:
        # Check for completed scheduled posts that haven't updated project status
        completed_posts = await db.execute(
            select(ScheduledPost).where(
                ScheduledPost.status == "completed",
                ScheduledPost.project_id.isnot(None)
            )
        )
        completed_posts = completed_posts.scalars().all()
        
        print(f"Found {len(completed_posts)} completed scheduled posts:")
        updated_count = 0
        for post in completed_posts:
            project = await db.get(Project, post.project_id)
            if project:
                print(f"Project: {project.name}, Current Status: {project.status}")
                if project.status == "Pending":
                    project.status = "Posted"
                    db.add(project)
                    updated_count += 1
                    print(f"Updated project '{project.name}' status from 'Pending' to 'Posted'")
        
        await db.commit()
        print(f"\nUpdated {updated_count} projects successfully!")
        
    finally:
        await db.aclose()

if __name__ == "__main__":
    asyncio.run(main()) 