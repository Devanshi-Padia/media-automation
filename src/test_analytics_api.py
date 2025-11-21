import asyncio
import httpx
from app.core.db.database import async_get_db
from app.models.analytics import PostAnalytics
from app.models.project import Project
from sqlalchemy import select

async def test_analytics_api():
    """Test the analytics API endpoints directly"""
    
    # First, check what data we have in the database
    async for db in async_get_db():
        try:
            # Check projects
            result = await db.execute(select(Project))
            projects = result.scalars().all()
            print(f"Found {len(projects)} projects")
            
            if projects:
                project = projects[0]
                print(f"Testing with project: {project.name} (ID: {project.id})")
                
                # Check analytics data for this project
                result = await db.execute(
                    select(PostAnalytics).where(PostAnalytics.project_id == project.id)
                )
                analytics = result.scalars().all()
                print(f"Found {len(analytics)} analytics records for project {project.id}")
                
                for a in analytics[:3]:
                    print(f"  Platform: {a.platform}, Likes: {a.likes}, Shares: {a.shares}, Comments: {a.comments}")
                
        except Exception as e:
            print(f"Database error: {e}")
            return
    
    # Now test the API endpoints
    async with httpx.AsyncClient() as client:
        try:
            # Test the performance endpoint
            response = await client.get(f"http://localhost:8000/api/v1/analytics/projects/{project.id}/performance")
            print(f"\nPerformance API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Performance data: {data}")
            else:
                print(f"Error response: {response.text}")
            
            # Test the summary endpoint
            response = await client.get(f"http://localhost:8000/api/v1/analytics/projects/{project.id}/summary")
            print(f"\nSummary API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Summary data: {data}")
            else:
                print(f"Error response: {response.text}")
                
        except Exception as e:
            print(f"API test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_analytics_api()) 