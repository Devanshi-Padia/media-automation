import asyncio
from datetime import datetime, timedelta
from app.core.db.database import async_get_db
from app.models.analytics import PostAnalytics
from app.models.project import Project
from sqlalchemy import select

async def create_sample_analytics():
    async for db in async_get_db():
        try:
            # First, check if we have any projects
            result = await db.execute(select(Project))
            projects = result.scalars().all()
            
            if not projects:
                print("No projects found. Please create a project first.")
                return
            
            print(f"Found {len(projects)} projects")
            
            # Check if we already have analytics data
            result = await db.execute(select(PostAnalytics))
            existing_analytics = result.scalars().all()
            
            if existing_analytics:
                print(f"Found {len(existing_analytics)} existing analytics records")
                for a in existing_analytics[:3]:
                    print(f"  Project {a.project_id}, Platform {a.platform}, Likes {a.likes}")
                return
            
            # Create sample analytics data for the first project
            project = projects[0]
            print(f"Creating sample analytics for project: {project.name} (ID: {project.id})")
            
            platforms = ['instagram', 'facebook', 'twitter', 'linkedin']
            
            for platform in platforms:
                # Create sample analytics data
                analytics = PostAnalytics(
                    post_id=None,
                    project_id=project.id,
                    platform=platform,
                    post_url=f"https://{platform}.com/sample-post",
                    likes=random.randint(50, 500),
                    shares=random.randint(10, 100),
                    comments=random.randint(5, 50),
                    reach=random.randint(1000, 10000),
                    impressions=random.randint(2000, 15000),
                    clicks=random.randint(20, 200),
                    engagement_rate=round(random.uniform(2.0, 8.0), 2),
                    click_through_rate=round(random.uniform(1.0, 5.0), 2),
                    ab_test_id=None,
                    variant=None,
                    data_quality_score=0.9,
                    is_anomaly=False,
                    last_verified=datetime.utcnow(),
                    last_synced=datetime.utcnow(),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                    updated_at=datetime.utcnow()
                )
                db.add(analytics)
            
            await db.commit()
            print("Sample analytics data created successfully!")
            
            # Verify the data was created
            result = await db.execute(select(PostAnalytics))
            new_analytics = result.scalars().all()
            print(f"Now have {len(new_analytics)} analytics records")
            
        except Exception as e:
            print(f"Error: {e}")
            await db.rollback()

if __name__ == "__main__":
    import random
    asyncio.run(create_sample_analytics()) 