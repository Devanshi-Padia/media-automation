#!/usr/bin/env python3
"""
Script to verify analytics data in the database.
"""

import asyncio
from sqlalchemy import select
from app.core.db.database import async_get_db
from app.models.analytics import PostAnalytics
from app.models.project import Project

async def main():
    """Main function to verify analytics data"""
    print("Verifying analytics data in the database...")
    
    try:
        db_gen = async_get_db()
        async for db in db_gen:
            # Check total analytics records
            analytics_result = await db.execute(select(PostAnalytics))
            analytics_records = analytics_result.scalars().all()
            
            print(f"Total analytics records: {len(analytics_records)}")
            
            if analytics_records:
                print("\nSample analytics records:")
                for i, record in enumerate(analytics_records[:5]):  # Show first 5 records
                    print(f"  Record {i+1}:")
                    print(f"    Project ID: {record.project_id}")
                    print(f"    Platform: {record.platform}")
                    print(f"    Likes: {record.likes}")
                    print(f"    Shares: {record.shares}")
                    print(f"    Comments: {record.comments}")
                    print(f"    Reach: {record.reach}")
                    print(f"    Impressions: {record.impressions}")
                    print(f"    Engagement Rate: {record.engagement_rate}%")
                    print(f"    Last Synced: {record.last_synced}")
                    print()
            
            # Check projects with analytics
            projects_result = await db.execute(select(Project))
            projects = projects_result.scalars().all()
            
            print(f"Total projects: {len(projects)}")
            
            # Count projects with analytics data
            projects_with_analytics = 0
            for project in projects:
                project_analytics = await db.scalar(
                    select(PostAnalytics).where(PostAnalytics.project_id == project.id)
                )
                if project_analytics:
                    projects_with_analytics += 1
            
            print(f"Projects with analytics data: {projects_with_analytics}")
            print(f"Projects without analytics data: {len(projects) - projects_with_analytics}")
            
            break
                
    except Exception as e:
        print(f"Error verifying analytics: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 