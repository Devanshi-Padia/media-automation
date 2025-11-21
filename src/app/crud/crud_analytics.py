from fastcrud import FastCRUD
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_, or_, desc, asc, select
import uuid

from ..models.analytics import PostAnalytics, ABTest, AnalyticsReport, AnalyticsTrend, AnalyticsInsight
from ..models.content import SocialMediaPost
from ..models.post import Post
from ..models.project import Project
from ..schemas.analytics import (
    PostAnalyticsCreate, PostAnalyticsUpdate, PostAnalyticsRead,
    ABTestCreate, ABTestUpdate, ABTestRead,
    AnalyticsReportCreate, AnalyticsReportUpdate, AnalyticsReportRead
)


# FastCRUD instances for analytics models
CRUDPostAnalytics = FastCRUD[PostAnalytics, PostAnalyticsCreate, PostAnalyticsUpdate, PostAnalyticsUpdate, PostAnalyticsRead, PostAnalyticsRead]
crud_post_analytics = CRUDPostAnalytics(PostAnalytics)

CRUDABTest = FastCRUD[ABTest, ABTestCreate, ABTestUpdate, ABTestUpdate, ABTestRead, ABTestRead]
crud_ab_test = CRUDABTest(ABTest)

CRUDAnalyticsReport = FastCRUD[AnalyticsReport, AnalyticsReportCreate, AnalyticsReportUpdate, AnalyticsReportUpdate, AnalyticsReportRead, AnalyticsReportRead]
crud_analytics_report = CRUDAnalyticsReport(AnalyticsReport)

# New CRUD instances for enhanced analytics
CRUDSocialMediaPost = FastCRUD[SocialMediaPost, None, None, None, None, None]
crud_social_media_post = CRUDSocialMediaPost(SocialMediaPost)

CRUDAnalyticsTrend = FastCRUD[AnalyticsTrend, None, None, None, None, None]
crud_analytics_trend = CRUDAnalyticsTrend(AnalyticsTrend)

CRUDAnalyticsInsight = FastCRUD[AnalyticsInsight, None, None, None, None, None]
crud_analytics_insight = CRUDAnalyticsInsight(AnalyticsInsight)


# Custom analytics functions
async def get_performance_summary(db: AsyncSession, project_id: int, days: int = 30) -> Dict[str, Any]:
    """Get performance summary for a project over a specified period"""
    try:
        print(f"[DEBUG] get_performance_summary called for project_id: {project_id}, days: {days}")
        start_date = datetime.utcnow() - timedelta(days=days)
        print(f"[DEBUG] start_date: {start_date}")
        
        # Test if PostAnalytics table exists and has data
        try:
            test_query = select(PostAnalytics).limit(1)
            test_result = await db.execute(test_query)
            test_analytics = test_result.scalars().all()
            print(f"[DEBUG] PostAnalytics table test - found {len(test_analytics)} records")
        except Exception as e:
            print(f"[DEBUG] PostAnalytics table test failed: {e}")
            return {
                "total_posts": 0,
                "total_engagement": 0,
                "average_engagement_rate": 0.0,
                "platform_breakdown": {},
                "top_performing_post": None
            }
        
        # Get analytics data
        try:
            query = select(PostAnalytics).where(
                    PostAnalytics.project_id == project_id,
                    PostAnalytics.created_at >= start_date
                )
            print(f"[DEBUG] Query: {query}")
            result = await db.execute(query)
            analytics = result.scalars().all()
            print(f"[DEBUG] Found {len(analytics)} analytics records")
        except Exception as e:
            print(f"[DEBUG] Error in analytics query: {e}")
            # Try without the date filter
            query = select(PostAnalytics).where(PostAnalytics.project_id == project_id)
            result = await db.execute(query)
            analytics = result.scalars().all()
            print(f"[DEBUG] Found {len(analytics)} analytics records (without date filter)")
        
        if not analytics:
            print(f"[DEBUG] No analytics found, returning default values")
            return {
                "total_posts": 0,
                "total_engagement": 0,
                "average_engagement_rate": 0.0,
                "platform_breakdown": {},
                "top_performing_post": None
            }
        
        # Calculate metrics
        total_engagement = sum(a.likes + a.shares + a.comments for a in analytics)
        total_likes = sum(a.likes for a in analytics)
        total_shares = sum(a.shares for a in analytics)
        total_comments = sum(a.comments for a in analytics)
        
        # Calculate average engagement rate properly
        if analytics:
            total_engagement_rate = sum(a.engagement_rate for a in analytics)
            avg_engagement_rate = total_engagement_rate / len(analytics)
        else:
            avg_engagement_rate = 0.0
        
        # Platform breakdown
        platform_breakdown = {}
        for analytics_record in analytics:
            platform = analytics_record.platform
            if platform not in platform_breakdown:
                platform_breakdown[platform] = {
                    "posts": 0,
                    "engagement": 0,
                    "likes": 0,
                    "shares": 0,
                    "comments": 0,
                    "reach": 0,
                    "impressions": 0,
                    "clicks": 0
                }
            
            platform_breakdown[platform]["posts"] += 1
            platform_breakdown[platform]["engagement"] += (
                analytics_record.likes + analytics_record.shares + analytics_record.comments
            )
            platform_breakdown[platform]["likes"] += analytics_record.likes
            platform_breakdown[platform]["shares"] += analytics_record.shares
            platform_breakdown[platform]["comments"] += analytics_record.comments
            platform_breakdown[platform]["reach"] += analytics_record.reach
            platform_breakdown[platform]["impressions"] += analytics_record.impressions
            platform_breakdown[platform]["clicks"] += analytics_record.clicks
        
        # Find top performing post
        top_post = max(analytics, key=lambda x: x.likes + x.shares + x.comments) if analytics else None
        
        # Calculate average click rate
        total_impressions = sum(a.impressions for a in analytics)
        total_clicks = sum(a.clicks for a in analytics)
        avg_click_rate = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
        
        result = {
            "total_posts": len(analytics),
            "total_engagement": total_engagement,
            "total_likes": total_likes,
            "total_shares": total_shares,
            "total_comments": total_comments,
            "average_engagement_rate": round(avg_engagement_rate, 2),
            "total_reach": sum(a.reach for a in analytics),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "average_click_rate": round(avg_click_rate, 2),
            "platform_breakdown": platform_breakdown,
            "top_performing_post": {
                "post_id": top_post.post_id,
                "platform": top_post.platform,
                "engagement": top_post.likes + top_post.shares + top_post.comments
            } if top_post else None
        }
        print(f"[DEBUG] Returning analytics summary: {result}")
        return result
        
    except Exception as e:
        print(f"[DEBUG] Error in get_performance_summary: {e}")
        return {
            "total_posts": 0,
            "total_engagement": 0,
            "average_engagement_rate": 0.0,
            "platform_breakdown": {},
            "top_performing_post": None
        }


async def update_analytics_metrics(db: AsyncSession, post_id: int, platform: str, metrics: Dict[str, Any]) -> PostAnalytics:
    """Update analytics metrics for a specific post and platform"""
    try:
        # Check if analytics record exists
        existing_record = await db.scalar(
            select(PostAnalytics).where(
                PostAnalytics.post_id == post_id,
                PostAnalytics.platform == platform
            )
        )
        
        if existing_record:
            # Update existing record
            existing_record.likes = metrics.get("likes", existing_record.likes)
            existing_record.shares = metrics.get("shares", existing_record.shares)
            existing_record.comments = metrics.get("comments", existing_record.comments)
            existing_record.reach = metrics.get("reach", existing_record.reach)
            existing_record.impressions = metrics.get("impressions", existing_record.impressions)
            existing_record.clicks = metrics.get("clicks", existing_record.clicks)
            existing_record.engagement_rate = metrics.get("engagement_rate", existing_record.engagement_rate)
            existing_record.click_through_rate = metrics.get("click_through_rate", existing_record.click_through_rate)
            existing_record.updated_at = datetime.utcnow()
            existing_record.last_synced = datetime.utcnow()
            
            await db.commit()
            return existing_record
        else:
            # Create new record
            new_record = PostAnalytics(
                post_id=post_id,
                platform=platform,
                likes=metrics.get("likes", 0),
                shares=metrics.get("shares", 0),
                comments=metrics.get("comments", 0),
                reach=metrics.get("reach", 0),
                impressions=metrics.get("impressions", 0),
                clicks=metrics.get("clicks", 0),
                engagement_rate=metrics.get("engagement_rate", 0.0),
                click_through_rate=metrics.get("click_through_rate", 0.0),
                last_synced=datetime.utcnow()
            )
            
            db.add(new_record)
            await db.commit()
            return new_record
            
    except Exception as e:
        await db.rollback()
        raise e


async def calculate_ab_test_results(db: AsyncSession, test_id: str) -> Dict[str, Any]:
    """Calculate results for an A/B test"""
    try:
        # Get A/B test
        test_query = select(ABTest).where(ABTest.test_id == test_id)
        test_result = await db.execute(test_query)
        test = test_result.scalar_one_or_none()
        
        if not test:
            return None
        
        # Get analytics data for this test
        analytics_query = select(PostAnalytics).where(
            PostAnalytics.ab_test_id == test_id
        )
        analytics_result = await db.execute(analytics_query)
        analytics_data = analytics_result.scalars().all()
        
        if not analytics_data:
            return {
                "test_id": test_id,
                "status": "no_data",
                "variants": {},
                "winner": None,
                "confidence_level": 0.0
            }
        
        # Group by variant
        variants = {}
        for analytics in analytics_data:
            variant = analytics.variant or "A"
            if variant not in variants:
                variants[variant] = {
                    "posts": 0,
                    "total_engagement": 0,
                    "total_reach": 0,
                    "avg_engagement_rate": 0.0,
                    "total_likes": 0,
                    "total_shares": 0,
                    "total_comments": 0
                }
            
            variants[variant]["posts"] += 1
            variants[variant]["total_engagement"] += (analytics.likes + analytics.shares + analytics.comments)
            variants[variant]["total_reach"] += analytics.reach
            variants[variant]["total_likes"] += analytics.likes
            variants[variant]["total_shares"] += analytics.shares
            variants[variant]["total_comments"] += analytics.comments
        
        # Calculate average engagement rates
        for variant in variants:
            if variants[variant]["posts"] > 0:
                variants[variant]["avg_engagement_rate"] = (
                    variants[variant]["total_engagement"] / variants[variant]["posts"]
                )
        
        # Determine winner (simplified - would need statistical significance testing)
        winner = None
        confidence_level = 0.0
        
        if len(variants) > 1:
            # Find variant with highest engagement rate
            best_variant = max(variants.keys(), key=lambda v: variants[v]["avg_engagement_rate"])
            best_rate = variants[best_variant]["avg_engagement_rate"]
            
            # Simple confidence calculation (would need proper statistical testing)
            other_rates = [variants[v]["avg_engagement_rate"] for v in variants if v != best_variant]
            if other_rates:
                avg_other_rate = sum(other_rates) / len(other_rates)
                if best_rate > avg_other_rate * 1.1:  # 10% improvement
                    winner = best_variant
                    confidence_level = min(0.95, (best_rate - avg_other_rate) / avg_other_rate)
        
        return {
            "test_id": test_id,
            "status": "completed",
            "variants": variants,
            "winner": winner,
            "confidence_level": confidence_level
        }
        
    except Exception as e:
        print(f"Error calculating A/B test results: {e}")
        return None


async def create_analytics_report(db: AsyncSession, report_data: AnalyticsReportCreate, user_id: int) -> AnalyticsReport:
    """Create a new analytics report"""
    try:
        report = AnalyticsReport(
            report_id=str(uuid.uuid4()),
            project_id=report_data.project_id,
            user_id=user_id,
            report_type=report_data.report_type,
            report_name=report_data.report_name,
            date_range=report_data.date_range,
            filters=report_data.filters,
            data={},
            format=report_data.format,
            status="generating"
        )
        
        db.add(report)
        await db.commit()
        return report
        
    except Exception as e:
        await db.rollback()
        raise e


async def mark_report_completed(db: AsyncSession, report_id: str, data: Dict[str, Any], file_path: Optional[str] = None) -> AnalyticsReport:
    """Mark an analytics report as completed"""
    try:
        report_query = select(AnalyticsReport).where(AnalyticsReport.report_id == report_id)
        report_result = await db.execute(report_query)
        report = report_result.scalar_one_or_none()
        
        if report:
            report.data = data
            report.status = "completed"
            report.completed_at = datetime.utcnow()
            if file_path:
                report.file_path = file_path
            
            await db.commit()
            return report
        
        return None
        
    except Exception as e:
        await db.rollback()
        raise e


# Enhanced analytics functions
async def get_analytics_trends(db: AsyncSession, project_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """Get analytics trends for a project"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get trend data
        trends_query = select(AnalyticsTrend).where(
            AnalyticsTrend.project_id == project_id,
            AnalyticsTrend.trend_date >= start_date
        ).order_by(AnalyticsTrend.trend_date.desc())
        
        result = await db.execute(trends_query)
        trends = result.scalars().all()
        
        return [
            {
                "platform": trend.platform,
                "trend_date": trend.trend_date,
                "period": trend.period,
                "total_posts": trend.total_posts,
                "total_engagement": trend.total_engagement,
                "total_reach": trend.total_reach,
                "avg_engagement_rate": trend.avg_engagement_rate,
                "engagement_growth": trend.engagement_growth,
                "reach_growth": trend.reach_growth
            }
            for trend in trends
        ]
        
    except Exception as e:
        print(f"Error getting analytics trends: {e}")
        return []


async def get_analytics_insights(db: AsyncSession, project_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get analytics insights for a project"""
    try:
        insights_query = select(AnalyticsInsight).where(
            AnalyticsInsight.project_id == project_id
        ).order_by(AnalyticsInsight.created_at.desc()).limit(limit)
        
        result = await db.execute(insights_query)
        insights = result.scalars().all()
        
        return [
            {
                "id": insight.id,
                "insight_type": insight.insight_type,
                "title": insight.title,
                "description": insight.description,
                "severity": insight.severity,
                "confidence": insight.confidence,
                "is_read": insight.is_read,
                "is_actioned": insight.is_actioned,
                "created_at": insight.created_at,
                "recommendations": insight.recommendations
            }
            for insight in insights
        ]
        
    except Exception as e:
        print(f"Error getting analytics insights: {e}")
        return []


async def mark_insight_as_read(db: AsyncSession, insight_id: int) -> bool:
    """Mark an insight as read"""
    try:
        insight_query = select(AnalyticsInsight).where(AnalyticsInsight.id == insight_id)
        insight_result = await db.execute(insight_query)
        insight = insight_result.scalar_one_or_none()
        
        if insight:
            insight.is_read = True
            await db.commit()
            return True
        
        return False
        
    except Exception as e:
        await db.rollback()
        print(f"Error marking insight as read: {e}")
        return False


async def mark_insight_as_actioned(db: AsyncSession, insight_id: int) -> bool:
    """Mark an insight as actioned"""
    try:
        insight_query = select(AnalyticsInsight).where(AnalyticsInsight.id == insight_id)
        insight_result = await db.execute(insight_query)
        insight = insight_result.scalar_one_or_none()
        
        if insight:
            insight.is_actioned = True
            insight.actioned_at = datetime.utcnow()
            await db.commit()
            return True
        
        return False
        
    except Exception as e:
        await db.rollback()
        print(f"Error marking insight as actioned: {e}")
        return False


async def get_data_quality_summary(db: AsyncSession, project_id: int) -> Dict[str, Any]:
    """Get data quality summary for a project"""
    try:
        # Get analytics data with quality scores
        analytics_query = select(PostAnalytics).where(
            PostAnalytics.project_id == project_id
        )
        result = await db.execute(analytics_query)
        analytics_data = result.scalars().all()
        
        if not analytics_data:
            return {
                "total_records": 0,
                "average_quality_score": 0.0,
                "quality_distribution": {},
                "anomalies_count": 0,
                "last_verified": None
            }
        
        # Calculate quality metrics
        total_records = len(analytics_data)
        average_quality_score = sum(a.data_quality_score for a in analytics_data) / total_records
        anomalies_count = sum(1 for a in analytics_data if a.is_anomaly)
        
        # Quality distribution
        quality_distribution = {
            "excellent": sum(1 for a in analytics_data if a.data_quality_score >= 0.9),
            "good": sum(1 for a in analytics_data if 0.7 <= a.data_quality_score < 0.9),
            "fair": sum(1 for a in analytics_data if 0.5 <= a.data_quality_score < 0.7),
            "poor": sum(1 for a in analytics_data if a.data_quality_score < 0.5)
        }
        
        # Last verification date
        last_verified = max(a.last_verified for a in analytics_data if a.last_verified) if any(a.last_verified for a in analytics_data) else None
        
        return {
            "total_records": total_records,
            "average_quality_score": round(average_quality_score, 2),
            "quality_distribution": quality_distribution,
            "anomalies_count": anomalies_count,
            "last_verified": last_verified
        }
        
    except Exception as e:
        print(f"Error getting data quality summary: {e}")
        return {
            "total_records": 0,
            "average_quality_score": 0.0,
            "quality_distribution": {},
            "anomalies_count": 0,
            "last_verified": None
        }


async def get_social_media_posts(db: AsyncSession, project_id: int) -> List[Dict[str, Any]]:
    """Get social media posts for a project"""
    try:
        posts_query = select(SocialMediaPost).where(
            SocialMediaPost.project_id == project_id
        ).order_by(SocialMediaPost.created_at.desc())
        
        result = await db.execute(posts_query)
        posts = result.scalars().all()
        
        return [
            {
                "id": post.id,
                "platform": post.platform,
                "platform_post_id": post.platform_post_id,
                "post_url": post.post_url,
                "status": post.status,
                "posted_at": post.posted_at,
                "created_at": post.created_at
            }
            for post in posts
        ]
        
    except Exception as e:
        print(f"Error getting social media posts: {e}")
        return [] 