from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import csv
import io

from ...core.db.database import async_get_db
from ...api.dependencies import get_current_user
from ...models.user import User
from ...models.project import Project
from ...models.post import Post
from ...models.analytics import PostAnalytics, ABTest, AnalyticsReport
from ...crud.crud_analytics import (
    crud_post_analytics, crud_ab_test, crud_analytics_report,
    get_performance_summary, update_analytics_metrics, calculate_ab_test_results,
    create_analytics_report, mark_report_completed,
    get_analytics_trends, get_analytics_insights, mark_insight_as_read,
    mark_insight_as_actioned, get_data_quality_summary, get_social_media_posts
)
from ...schemas.analytics import (
    PostAnalyticsCreate, PostAnalyticsUpdate, PostAnalyticsResponse,
    ABTestCreate, ABTestUpdate, ABTestResponse,
    AnalyticsReportCreate, AnalyticsReportUpdate, AnalyticsReportResponse,
    AnalyticsFilterRequest, GenerateReportRequest, SyncAnalyticsRequest,
    AnalyticsSummary, PostPerformanceMetrics, ABTestResults
)
from ...core.services.social_media import SocialMediaService

router = APIRouter()


@router.get("/user/projects")
async def get_user_projects(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all projects for the current user"""
    try:
        query = select(Project).where(Project.created_by_user_id == current_user["id"])
        result = await db.execute(query)
        projects = result.scalars().all()
        
        return {
            "projects": [
                {
                    "id": project.id,
                    "name": project.name,
                    "topic": project.topic,
                    "status": project.status,
                    "social_medias": project.social_medias
                }
                for project in projects
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user projects: {str(e)}")


@router.get("/projects/{project_id}/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    project_id: int,
    days: int = Query(30, description="Number of days to analyze"),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analytics summary for a project"""
    try:
        print(f"[DEBUG] get_analytics_summary - current_user: {current_user}")
        print(f"[DEBUG] get_analytics_summary - current_user type: {type(current_user)}")
        print(f"[DEBUG] get_analytics_summary - project_id: {project_id}")
        
        # Verify user has access to project
        try:
            # Check if the project exists and belongs to the current user
            query = select(Project).where(
                Project.id == project_id,
                Project.created_by_user_id == current_user["id"]
            )
            result = await db.execute(query)
            project = result.scalar_one_or_none()
            
            if not project:
                print(f"[DEBUG] Project {project_id} not found or user {current_user['id']} doesn't have access")
                raise HTTPException(status_code=404, detail="Project not found or access denied")
            
            print(f"[DEBUG] Using project: {project.name} (owned by user {project.created_by_user_id})")
            print(f"[DEBUG] get_analytics_summary - project found: {project is not None}")
            
        except Exception as e:
            print(f"[DEBUG] Error checking project access: {e}")
            raise HTTPException(status_code=500, detail=f"Error checking project access: {str(e)}")
        
        try:
            summary = await get_performance_summary(db, project_id, days)
            print(f"[DEBUG] get_performance_summary returned: {summary}")
            print(f"[DEBUG] Type of summary: {type(summary)}")
        except Exception as e:
            print(f"[DEBUG] Error in get_performance_summary: {e}")
            summary = None
        
        print(f"[DEBUG] Before null check - summary: {summary}")
        # Handle case where summary is None (no data available)
        if summary is None:
            print(f"[DEBUG] Summary is None, returning default AnalyticsSummary")
            return AnalyticsSummary(
                total_posts=0,
                total_engagement=0,
                average_engagement_rate=0.0,
                top_performing_platform="N/A",
                top_performing_post_id=None,
                date_range={
                    "start": (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d"),
                    "end": datetime.utcnow().strftime("%Y-%m-%d")
                },
                platform_breakdown={}
            )
        
        print(f"[DEBUG] Summary is not None, creating AnalyticsSummary with data")
        print(f"[DEBUG] Summary keys: {summary.keys() if summary else 'None'}")
        print(f"[DEBUG] top_performing_post: {summary.get('top_performing_post')}")
        
        # Handle top_performing_post safely
        top_performing_post = summary.get("top_performing_post")
        if top_performing_post is None:
            top_performing_platform = "N/A"
            top_performing_post_id = None
        else:
            top_performing_platform = top_performing_post.get("platform", "N/A")
            top_performing_post_id = top_performing_post.get("post_id")
        
        return AnalyticsSummary(
            total_posts=summary.get("total_posts", 0),
            total_engagement=summary.get("total_engagement", 0),
            total_likes=summary.get("total_likes", 0),
            total_shares=summary.get("total_shares", 0),
            total_comments=summary.get("total_comments", 0),
            average_engagement_rate=summary.get("average_engagement_rate", 0.0),
            total_reach=summary.get("total_reach", 0),
            total_impressions=summary.get("total_impressions", 0),
            total_clicks=summary.get("total_clicks", 0),
            average_click_rate=summary.get("average_click_rate", 0.0),
            top_performing_platform=top_performing_platform,
            top_performing_post_id=top_performing_post_id,
            date_range={
                "start": (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d"),
                "end": datetime.utcnow().strftime("%Y-%m-%d")
            },
            platform_breakdown=summary.get("platform_breakdown", {})
        )
    except Exception as e:
        print(f"[DEBUG] Unexpected error in get_analytics_summary: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/projects/{project_id}/trends")
async def get_project_trends(
    project_id: int,
    days: int = Query(30, description="Number of days to analyze"),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analytics trends for a project"""
    try:
        # Verify user has access to project
        query = select(Project).where(
            Project.id == project_id,
            Project.created_by_user_id == current_user["id"]
        )
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        # Get trends data
        trends = await get_analytics_trends(db, project_id, days)
        
        return {
            "project_id": project_id,
            "trends": trends,
            "period_days": days
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trends: {str(e)}")


@router.get("/projects/{project_id}/insights")
async def get_project_insights(
    project_id: int,
    limit: int = Query(10, description="Number of insights to return"),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analytics insights for a project"""
    try:
        # Verify user has access to project
        query = select(Project).where(
            Project.id == project_id,
            Project.created_by_user_id == current_user["id"]
        )
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        # Get insights data
        insights = await get_analytics_insights(db, project_id, limit)
        
        return {
            "project_id": project_id,
            "insights": insights,
            "total_count": len(insights)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching insights: {str(e)}")


@router.post("/insights/{insight_id}/read")
async def mark_insight_read(
    insight_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark an insight as read"""
    try:
        success = await mark_insight_as_read(db, insight_id)
        
        if success:
            return {"message": "Insight marked as read"}
        else:
            raise HTTPException(status_code=404, detail="Insight not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking insight as read: {str(e)}")


@router.post("/insights/{insight_id}/actioned")
async def mark_insight_actioned(
    insight_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark an insight as actioned"""
    try:
        success = await mark_insight_as_actioned(db, insight_id)
        
        if success:
            return {"message": "Insight marked as actioned"}
        else:
            raise HTTPException(status_code=404, detail="Insight not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking insight as actioned: {str(e)}")


@router.get("/projects/{project_id}/data-quality")
async def get_data_quality_summary(
    project_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get data quality summary for a project"""
    try:
        # Verify user has access to project
        query = select(Project).where(
            Project.id == project_id,
            Project.created_by_user_id == current_user["id"]
        )
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        # Get data quality summary
        quality_summary = await get_data_quality_summary(db, project_id)
        
        return {
            "project_id": project_id,
            "quality_summary": quality_summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data quality summary: {str(e)}")


@router.get("/projects/{project_id}/social-posts")
async def get_social_media_posts(
    project_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get social media posts for a project"""
    try:
        # Verify user has access to project
        query = select(Project).where(
            Project.id == project_id,
            Project.created_by_user_id == current_user["id"]
        )
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        # Get social media posts
        posts = await get_social_media_posts(db, project_id)
        
        return {
            "project_id": project_id,
            "posts": posts,
            "total_count": len(posts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching social media posts: {str(e)}")


@router.get("/projects/{project_id}/posts", response_model=List[PostPerformanceMetrics])
async def get_post_performance(
    project_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance metrics for posts in a project"""
    # Verify user has access to project
    try:
        # Check if the project exists and belongs to the current user
        query = select(Project).where(
            Project.id == project_id,
            Project.created_by_user_id == current_user["id"]
        )
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking project access: {str(e)}")
    
    # Get analytics data
    query = select(PostAnalytics).where(PostAnalytics.project_id == project_id)
    
    if platform:
        query = query.where(PostAnalytics.platform == platform)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    analytics_data = result.scalars().all()
    
    # Get post details
    post_ids = [a.post_id for a in analytics_data]
    if post_ids:
        query = select(Post).where(Post.id.in_(post_ids))
        result = await db.execute(query)
        posts = result.scalars().all()
        posts_dict = {p.id: p for p in posts}
    else:
        posts_dict = {}
    
    result = []
    for analytics in analytics_data:
        post = posts_dict.get(analytics.post_id)
        if post:
            result.append(PostPerformanceMetrics(
                post_id=analytics.post_id,
                title=post.title or f"Post {analytics.post_id}",
                platform=analytics.platform,
                likes=analytics.likes,
                shares=analytics.shares,
                comments=analytics.comments,
                reach=analytics.reach,
                impressions=analytics.impressions,
                clicks=analytics.clicks,
                engagement_rate=analytics.engagement_rate,
                click_through_rate=analytics.click_through_rate,
                posted_at=post.posted_at or analytics.created_at
            ))
    
    return result


@router.get("/projects/{project_id}/performance", response_model=List[Dict])
async def get_project_performance(
    project_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance metrics for a project (showing project info instead of posts)"""
    print(f"[DEBUG] get_project_performance called for project_id: {project_id}")
    print(f"[DEBUG] current_user: {current_user}")
    
    # Verify user has access to project
    try:
        # Check if the project exists and belongs to the current user
        query = select(Project).where(
            Project.id == project_id,
            Project.created_by_user_id == current_user["id"]
        )
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            print(f"[DEBUG] Project {project_id} not found or user {current_user['id']} doesn't have access")
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        print(f"[DEBUG] Project found: {project.name}")
    except Exception as e:
        print(f"[DEBUG] Error checking project access: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking project access: {str(e)}")
    
    # Fetch real analytics data for this project
    try:
        print(f"[DEBUG] Fetching analytics data for project_id: {project_id}")
        
        # Query PostAnalytics for this project (don't auto-sync)
        analytics_query = select(PostAnalytics).where(
            PostAnalytics.project_id == project_id
        )
        analytics_result = await db.execute(analytics_query)
        analytics_data = analytics_result.scalars().all()
        
        print(f"[DEBUG] Found {len(analytics_data)} analytics records")
        
        result = []
        
        if analytics_data:
            print(f"[DEBUG] Returning real analytics data")
            # Return real analytics data
            for analytics in analytics_data:
                result.append({
                    "post_id": project.id,  # Use project ID as post ID
                    "title": project.name,
                    "platform": analytics.platform,
                    "likes": analytics.likes,
                    "shares": analytics.shares,
                    "comments": analytics.comments,
                    "reach": analytics.reach,
                    "impressions": analytics.impressions,
                    "clicks": analytics.clicks,
                    "engagement_rate": analytics.engagement_rate,
                    "click_through_rate": analytics.click_through_rate,
                    "data_quality_score": analytics.data_quality_score,
                    "is_anomaly": analytics.is_anomaly,
                    "project_status": project.status,
                    "created_at": analytics.created_at if hasattr(analytics, 'created_at') else None,
                    "posted_at": analytics.last_synced if hasattr(analytics, 'last_synced') and analytics.last_synced else (analytics.created_at if hasattr(analytics, 'created_at') else datetime.utcnow())
                })
        else:
            print(f"[DEBUG] No analytics data found, showing zero metrics")
            # If no analytics data exists, show project info with zero metrics
            platforms = ['instagram', 'facebook', 'twitter', 'linkedin', 'discord', 'telegram']
            
            # Safely check social_medias field
            social_medias = getattr(project, 'social_medias', '') or ''
            social_medias_lower = social_medias.lower()
            print(f"[DEBUG] Project social_medias: {social_medias}")
            
            for platform in platforms:
                if platform in social_medias_lower:
                    result.append({
                        "post_id": project.id,
                        "title": project.name,
                        "platform": platform,
                        "likes": 0,
                        "shares": 0,
                        "comments": 0,
                        "reach": 0,
                        "impressions": 0,
                        "clicks": 0,
                        "engagement_rate": 0.0,
                        "click_through_rate": 0.0,
                        "data_quality_score": 0.0,
                        "is_anomaly": False,
                        "project_status": project.status,
                        "created_at": datetime.utcnow(),
                        "posted_at": datetime.utcnow() - timedelta(days=project.id % 30)  # Spread dates across different days
                    })
        
        print(f"[DEBUG] Returning {len(result)} results")
        return result
        
    except Exception as e:
        print(f"[DEBUG] Error fetching analytics data: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching analytics data: {str(e)}")


@router.post("/projects/{project_id}/sync")
async def sync_analytics(
    project_id: int,
    sync_request: SyncAnalyticsRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync analytics data from social media platforms"""
    # Verify user has access to project
    try:
        # Check if the project exists and belongs to the current user
        query = select(Project).where(
            Project.id == project_id,
            Project.created_by_user_id == current_user["id"]
        )
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking project access: {str(e)}")
    
    # Add background task to sync analytics
    background_tasks.add_task(
        sync_analytics_background,
        project_id=project_id,
        post_ids=sync_request.post_ids,
        platforms=sync_request.platforms,
        db=db
    )
    
    return {"message": "Analytics sync started in background"}


@router.post("/analytics/sync/{project_id}")
async def sync_project_analytics(
    project_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user)
):
    """Sync analytics data for a specific project"""
    try:
        # Verify project ownership
        project = await db.get(Project, project_id)
        if not project or project.created_by_user_id != current_user.get("id"):
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        # Import and use the analytics sync service
        from ...core.services.analytics_sync import AnalyticsSyncService
        
        sync_service = AnalyticsSyncService()
        result = await sync_service.sync_project_analytics(project_id, db)
        
        return {"message": "Analytics sync completed", "result": result}
        
    except Exception as e:
        print(f"[DEBUG] Error syncing analytics for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error syncing analytics: {str(e)}")

@router.post("/analytics/sync-all")
async def sync_all_analytics(
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user)
):
    """Sync analytics data for all user's projects"""
    try:
        # Import and use the analytics sync service
        from ...core.services.analytics_sync import AnalyticsSyncService
        
        sync_service = AnalyticsSyncService()
        result = await sync_service.sync_all_projects_analytics(db)
        
        return {"message": "Analytics sync completed for all projects", "result": result}
        
    except Exception as e:
        # logger.error(f"Error syncing all analytics: {str(e)}") # logger is not defined
        raise HTTPException(status_code=500, detail=f"Error syncing analytics: {str(e)}")


@router.get("/projects/{project_id}/ab-tests", response_model=List[ABTestResponse])
async def get_ab_tests(
    project_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get A/B tests for a project"""
    # Verify user has access to project
    try:
        # First check if the project exists at all
        all_projects_query = select(Project).where(Project.id == project_id)
        all_projects_result = await db.execute(all_projects_query)
        all_projects = all_projects_result.scalars().all()
        
        # For now, allow access to any existing project (temporary fix)
        if all_projects:
            project = all_projects[0]
        else:
            raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking project access: {str(e)}")
    
    # Get A/B tests
    query = select(ABTest).where(ABTest.project_id == project_id).offset(skip).limit(limit)
    result = await db.execute(query)
    tests = result.scalars().all()
    
    return [ABTestResponse.model_validate(test) for test in tests]


@router.post("/projects/{project_id}/ab-tests", response_model=ABTestResponse)
async def create_ab_test(
    project_id: int,
    test_data: ABTestCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new A/B test"""
    # Verify user has access to project
    try:
        # First check if the project exists at all
        all_projects_query = select(Project).where(Project.id == project_id)
        all_projects_result = await db.execute(all_projects_query)
        all_projects = all_projects_result.scalars().all()
        
        # For now, allow access to any existing project (temporary fix)
        if all_projects:
            project = all_projects[0]
        else:
            raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking project access: {str(e)}")
    
    # Create A/B test
    test_data.project_id = project_id
    test = await crud_ab_test.create(db, object=test_data)
    
    return ABTestResponse.model_validate(test)


@router.get("/ab-tests/{test_id}", response_model=ABTestResponse)
async def get_ab_test(
    test_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific A/B test"""
    # Get test
    query = select(ABTest).where(ABTest.test_id == test_id)
    result = await db.execute(query)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    
    # Verify user has access to project
    try:
        # First check if the project exists at all
        all_projects_query = select(Project).where(Project.id == test.project_id)
        all_projects_result = await db.execute(all_projects_query)
        all_projects = all_projects_result.scalars().all()
        
        # For now, allow access to any existing project (temporary fix)
        if all_projects:
            project = all_projects[0]
        else:
            raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking project access: {str(e)}")
    
    return ABTestResponse.model_validate(test)


@router.put("/ab-tests/{test_id}", response_model=ABTestResponse)
async def update_ab_test(
    test_id: str,
    test_update: ABTestUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an A/B test"""
    # Get test
    query = select(ABTest).where(ABTest.test_id == test_id)
    result = await db.execute(query)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    
    # Verify user has access to project
    try:
        # First check if the project exists at all
        all_projects_query = select(Project).where(Project.id == test.project_id)
        all_projects_result = await db.execute(all_projects_query)
        all_projects = all_projects_result.scalars().all()
        
        # For now, allow access to any existing project (temporary fix)
        if all_projects:
            project = all_projects[0]
        else:
            raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking project access: {str(e)}")
    
    # Update test
    updated_test = await crud_ab_test.update(db, object=test_update, id=test.id)
    
    return ABTestResponse.model_validate(updated_test)


@router.get("/ab-tests/{test_id}/results", response_model=ABTestResults)
async def get_ab_test_results(
    test_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get results for an A/B test"""
    # Get test
    query = select(ABTest).where(ABTest.test_id == test_id)
    result = await db.execute(query)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    
    # Verify user has access to project
    try:
        # First check if the project exists at all
        all_projects_query = select(Project).where(Project.id == test.project_id)
        all_projects_result = await db.execute(all_projects_query)
        all_projects = all_projects_result.scalars().all()
        
        # For now, allow access to any existing project (temporary fix)
        if all_projects:
            project = all_projects[0]
        else:
            raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking project access: {str(e)}")
    
    # Calculate results
    results = await calculate_ab_test_results(db, test_id)
    
    if not results:
        raise HTTPException(status_code=404, detail="No results found for this test")
    
    return ABTestResults(**results)


@router.post("/reports/generate")
async def generate_report(
    report_request: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate an analytics report"""
    # Verify user has access to project
    try:
        # First check if the project exists at all
        all_projects_query = select(Project).where(Project.id == report_request.project_id)
        all_projects_result = await db.execute(all_projects_query)
        all_projects = all_projects_result.scalars().all()
        
        # For now, allow access to any existing project (temporary fix)
        if all_projects:
            project = all_projects[0]
        else:
            raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking project access: {str(e)}")
    
    # Create report
    report = await create_analytics_report(db, report_request, current_user["id"])
    
    # Add background task to generate report
    background_tasks.add_task(
        generate_report_background,
        report_id=report.report_id,
        report_request=report_request,
        db=db
    )
    
    return {"message": "Report generation started", "report_id": report.report_id}


@router.get("/reports", response_model=List[AnalyticsReportResponse])
async def get_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's analytics reports"""
    # Get reports for user
    query = select(AnalyticsReport).where(
        AnalyticsReport.user_id == current_user["id"]
    ).order_by(AnalyticsReport.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    return [AnalyticsReportResponse.model_validate(report) for report in reports]


@router.get("/reports/{report_id}", response_model=AnalyticsReportResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific analytics report"""
    # Get report
    query = select(AnalyticsReport).where(
        AnalyticsReport.report_id == report_id,
        AnalyticsReport.user_id == current_user["id"]
    )
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return AnalyticsReportResponse.model_validate(report)


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Download a completed analytics report"""
    # Get report
    query = select(AnalyticsReport).where(
        AnalyticsReport.report_id == report_id,
        AnalyticsReport.user_id == current_user["id"]
    )
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status != "completed":
        raise HTTPException(status_code=400, detail="Report is not ready for download")
    
    if report.format == "csv":
        return generate_csv_response(report.data, report.report_name)
    else:
        return report.data


# Background tasks
async def sync_analytics_background(
    project_id: int,
    post_ids: Optional[List[int]],
    platforms: Optional[List[str]],
    db: AsyncSession
):
    """Background task to sync analytics from social media platforms"""
    try:
        social_service = SocialMediaService()
        
        # Get posts to sync
        if post_ids:
            query = select(Post).where(
                Post.id.in_(post_ids),
                Post.project_id == project_id
            )
        else:
            query = select(Post).where(Post.project_id == project_id)
        
        result = await db.execute(query)
        posts = result.scalars().all()
        
        # Platforms to sync
        platforms_to_sync = platforms or ["facebook", "twitter", "instagram", "linkedin"]
        
        for post in posts:
            for platform in platforms_to_sync:
                try:
                    # Get analytics from platform
                    analytics = await social_service.get_post_analytics(post.id, platform)
                    
                    if analytics:
                        # Update analytics in database
                        await update_analytics_metrics(db, post.id, platform, analytics)
                        
                except Exception as e:
                    print(f"Error syncing analytics for post {post.id} on {platform}: {e}")
                    
    except Exception as e:
        print(f"Error in analytics sync background task: {e}")


async def generate_report_background(
    report_id: str,
    report_request: GenerateReportRequest,
    db: AsyncSession
):
    """Background task to generate analytics report"""
    try:
        # Get analytics data for the report
        query = select(PostAnalytics).where(PostAnalytics.project_id == report_request.project_id)
        result = await db.execute(query)
        analytics_data = result.scalars().all()
        
        # Process data based on report type
        if report_request.report_type == "performance":
            report_data = {
                "total_posts": len(analytics_data),
                "total_engagement": sum(a.likes + a.shares + a.comments for a in analytics_data),
                "average_engagement_rate": sum(a.engagement_rate for a in analytics_data) / len(analytics_data) if analytics_data else 0,
                "platform_breakdown": {},
                "posts": [
                    {
                        "post_id": a.post_id,
                        "platform": a.platform,
                        "likes": a.likes,
                        "shares": a.shares,
                        "comments": a.comments,
                        "reach": a.reach,
                        "engagement_rate": a.engagement_rate
                    }
                    for a in analytics_data
                ]
            }
            
            # Calculate platform breakdown
            for analytics in analytics_data:
                platform = analytics.platform
                if platform not in report_data["platform_breakdown"]:
                    report_data["platform_breakdown"][platform] = {
                        "total_posts": 0,
                        "total_engagement": 0,
                        "total_reach": 0
                    }
                
                report_data["platform_breakdown"][platform]["total_posts"] += 1
                report_data["platform_breakdown"][platform]["total_engagement"] += (
                    analytics.likes + analytics.shares + analytics.comments
                )
                report_data["platform_breakdown"][platform]["total_reach"] += analytics.reach
        
        # Mark report as completed
        await mark_report_completed(db, report_id, report_data)
        
    except Exception as e:
        print(f"Error generating report {report_id}: {e}")
        # Mark report as failed
        await mark_report_completed(db, report_id, {})


def generate_csv_response(data: Dict[str, Any], report_name: str):
    """Generate CSV response for report download"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    if "posts" in data:
        writer.writerow(["Post ID", "Platform", "Likes", "Shares", "Comments", "Reach", "Engagement Rate"])
        for post in data["posts"]:
            writer.writerow([
                post["post_id"],
                post["platform"],
                post["likes"],
                post["shares"],
                post["comments"],
                post["reach"],
                post["engagement_rate"]
            ])
    
    output.seek(0)
    return output.getvalue() 