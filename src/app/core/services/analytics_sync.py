import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import requests
import time
import random

from ...models.analytics import PostAnalytics, AnalyticsTrend, AnalyticsInsight
from ...models.content import SocialMediaPost
from ...models.project import Project, SocialMediaCredential
from ...models.content import ContentGeneration
from ...core.db.database import async_get_db
from .social_media_apis import TwitterAPI, FacebookAPI, InstagramAPI, LinkedInAPI, DiscordAPI, TelegramAPI

logger = logging.getLogger(__name__)

class AnalyticsDataValidator:
    """Validate analytics data quality and consistency"""
    
    @staticmethod
    def validate_metrics(data: Dict[str, Any]) -> tuple[bool, float, str]:
        """
        Validate analytics metrics and return (is_valid, quality_score, error_message)
        """
        quality_score = 1.0
        errors = []
        
        # Check for negative values
        for metric in ['likes', 'shares', 'comments', 'reach', 'impressions', 'clicks']:
            if data.get(metric, 0) < 0:
                errors.append(f"Negative {metric}: {data.get(metric)}")
                quality_score -= 0.2
        
        # Check for impossible relationships
        if data.get('likes', 0) > data.get('reach', 0) and data.get('reach', 0) > 0:
            errors.append(f"Likes ({data.get('likes')}) exceed reach ({data.get('reach')})")
            quality_score -= 0.3
        
        if data.get('comments', 0) > data.get('reach', 0) and data.get('reach', 0) > 0:
            errors.append(f"Comments ({data.get('comments')}) exceed reach ({data.get('reach')})")
            quality_score -= 0.2
        
        # Check for reasonable engagement rates
        engagement_rate = data.get('engagement_rate', 0)
        if engagement_rate > 100:
            errors.append(f"Unrealistic engagement rate: {engagement_rate}%")
            quality_score -= 0.4
        elif engagement_rate > 50:
            errors.append(f"Very high engagement rate: {engagement_rate}%")
            quality_score -= 0.1
        
        # Check for zero values (might indicate API failure)
        all_zero = all(data.get(metric, 0) == 0 for metric in ['likes', 'shares', 'comments', 'reach', 'impressions'])
        if all_zero:
            errors.append("All metrics are zero - possible API failure")
            quality_score -= 0.5
        
        quality_score = max(0.0, quality_score)
        is_valid = quality_score > 0.5
        
        return is_valid, quality_score, "; ".join(errors) if errors else "Data is valid"

class AnalyticsSyncService:
    """Enhanced service to sync analytics data from social media platforms"""
    
    def __init__(self):
        self.platform_apis = {
            'twitter': self._fetch_twitter_analytics,
            'facebook': self._fetch_facebook_analytics,
            'instagram': self._fetch_instagram_analytics,
            'linkedin': self._fetch_linkedin_analytics,
            'discord': self._fetch_discord_analytics,
            'telegram': self._fetch_telegram_analytics,
        }
        self.validator = AnalyticsDataValidator()
    
    async def sync_project_analytics(self, project_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Sync analytics for a specific project with enhanced error handling"""
        try:
            # Get project and its credentials
            project = await db.get(Project, project_id)
            if not project:
                return {"error": "Project not found"}
            
            # Get social media credentials
            creds_result = await db.execute(
                select(SocialMediaCredential).where(SocialMediaCredential.project_id == project_id)
            )
            credentials = creds_result.scalars().all()
            
            if not credentials:
                return {"error": "No social media credentials found for project"}
            
            # Get content generation for this project
            content_gen = await db.scalar(
                select(ContentGeneration).where(ContentGeneration.project_id == project_id)
            )
            
            if not content_gen:
                return {"error": "No content generation found for project"}
            
            # Get actual social media posts
            posts_result = await db.execute(
                select(SocialMediaPost).where(SocialMediaPost.project_id == project_id)
            )
            social_posts = posts_result.scalars().all()
            
            # Sync analytics for each platform
            results = {}
            insights_generated = []
            
            for cred in credentials:
                platform = cred.platform.lower()
                if platform in self.platform_apis:
                    try:
                        # Find actual post for this platform
                        platform_post = next((p for p in social_posts if p.platform == platform), None)
                        
                        if platform_post:
                            # Use real post ID
                            analytics_data = await self._fetch_analytics_with_retry(
                                platform, cred, platform_post.platform_post_id, db
                            )
                        else:
                            # Fallback to content generation ID
                            analytics_data = await self._fetch_analytics_with_retry(
                                platform, cred, str(content_gen.id), db
                            )
                        
                        if analytics_data:
                            # Validate data quality
                            is_valid, quality_score, validation_message = self.validator.validate_metrics(analytics_data)
                            
                            if is_valid:
                                await self._save_analytics_record(project_id, platform, analytics_data, quality_score, db)
                                results[platform] = {"status": "success", "quality_score": quality_score}
                                
                                # Generate insights for high-quality data
                                if quality_score > 0.8:
                                    insight = await self._generate_insight(project_id, platform, analytics_data, db)
                                    if insight:
                                        insights_generated.append(insight)
                            else:
                                logger.warning(f"Low quality data for {platform}: {validation_message}")
                                results[platform] = {"status": "low_quality", "quality_score": quality_score, "message": validation_message}
                        else:
                            results[platform] = {"status": "no_data", "quality_score": 0.0}
                            
                    except Exception as e:
                        logger.error(f"Error syncing {platform} analytics: {str(e)}")
                        results[platform] = {"status": "error", "error": str(e), "quality_score": 0.0}
            
            # Update trends
            await self._update_analytics_trends(project_id, db)
            
            return {
                "results": results,
                "insights_generated": len(insights_generated),
                "total_platforms": len(credentials)
            }
            
        except Exception as e:
            logger.error(f"Error in sync_project_analytics: {str(e)}")
            return {"error": str(e)}
    
    async def _fetch_analytics_with_retry(self, platform: str, credentials: SocialMediaCredential, post_id: str, db: AsyncSession, max_retries: int = 3) -> Optional[Dict]:
        """Fetch analytics with exponential backoff retry logic"""
        for attempt in range(max_retries):
            try:
                analytics_data = await self.platform_apis[platform](credentials, post_id, db)
                
                if analytics_data:
                    return analytics_data
                else:
                    logger.warning(f"No data returned from {platform} API (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.error(f"Error fetching {platform} analytics (attempt {attempt + 1}): {str(e)}")
                
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch {platform} analytics after {max_retries} attempts")
                    return None
                
                # Exponential backoff with jitter
                delay = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(delay)
        
        return None
    
    async def _fetch_twitter_analytics(self, credentials: SocialMediaCredential, post_id: str, db: AsyncSession) -> Optional[Dict]:
        """Fetch Twitter/X analytics data using real API"""
        try:
            # Initialize Twitter API with credentials
            twitter_api = TwitterAPI(
                api_key=credentials.twitter_api_key or "",
                api_secret=credentials.twitter_api_secret or "",
                access_token=credentials.twitter_access_token or "",
                access_secret=credentials.twitter_access_secret or ""
            )
            
            # Get real analytics from Twitter API
            analytics_data = twitter_api.get_tweet_analytics(post_id)
            
            if analytics_data:
                return analytics_data
            else:
                logger.warning(f"Twitter API returned no data for post {post_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching Twitter analytics: {str(e)}")
            return None
    
    async def _fetch_facebook_analytics(self, credentials: SocialMediaCredential, post_id: str, db: AsyncSession) -> Optional[Dict]:
        """Fetch Facebook analytics data using real API"""
        try:
            # Initialize Facebook API with credentials
            facebook_api = FacebookAPI(
                page_id=credentials.fb_page_id or "",
                access_token=credentials.fb_page_access_token or ""
            )
            
            # Get real analytics from Facebook API
            analytics_data = facebook_api.get_post_analytics(post_id)
            
            if analytics_data:
                return analytics_data
            else:
                logger.warning(f"Facebook API returned no data for post {post_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching Facebook analytics: {str(e)}")
            return None
    
    async def _fetch_instagram_analytics(self, credentials: SocialMediaCredential, post_id: str, db: AsyncSession) -> Optional[Dict]:
        """Fetch Instagram analytics data using real API"""
        try:
            # Initialize Instagram API with credentials
            instagram_api = InstagramAPI(
                access_token=credentials.ig_username or ""  # Using username as token for now
            )
            
            # Get real analytics from Instagram API
            analytics_data = instagram_api.get_post_analytics(post_id)
            
            if analytics_data:
                return analytics_data
            else:
                logger.warning(f"Instagram API returned no data for post {post_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching Instagram analytics: {str(e)}")
            return None
    
    async def _fetch_linkedin_analytics(self, credentials: SocialMediaCredential, post_id: str, db: AsyncSession) -> Optional[Dict]:
        """Fetch LinkedIn analytics data using real API"""
        try:
            # Initialize LinkedIn API with credentials
            linkedin_api = LinkedInAPI(
                access_token=credentials.linkedin_access_token or ""
            )
            
            # Get real analytics from LinkedIn API
            analytics_data = linkedin_api.get_post_analytics(post_id)
            
            if analytics_data:
                return analytics_data
            else:
                logger.warning(f"LinkedIn API returned no data for post {post_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching LinkedIn analytics: {str(e)}")
            return None
    
    async def _fetch_discord_analytics(self, credentials: SocialMediaCredential, post_id: str, db: AsyncSession) -> Optional[Dict]:
        """Fetch Discord analytics data using real API"""
        try:
            # Initialize Discord API with credentials
            discord_api = DiscordAPI(
                webhook_url=credentials.discord_webhook_url or ""
            )
            
            # Get real analytics from Discord API
            analytics_data = discord_api.get_message_analytics(post_id)
            
            if analytics_data:
                return analytics_data
            else:
                logger.warning(f"Discord API returned no data for message {post_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching Discord analytics: {str(e)}")
            return None
    
    async def _fetch_telegram_analytics(self, credentials: SocialMediaCredential, post_id: str, db: AsyncSession) -> Optional[Dict]:
        """Fetch Telegram analytics data using real API"""
        try:
            # Initialize Telegram API with credentials
            telegram_api = TelegramAPI(
                bot_token=credentials.telegram_bot_token or "",
                channel_id=credentials.telegram_channel_id or ""
            )
            
            # Get real analytics from Telegram API
            analytics_data = telegram_api.get_message_analytics(post_id)
            
            if analytics_data:
                return analytics_data
            else:
                logger.warning(f"Telegram API returned no data for message {post_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching Telegram analytics: {str(e)}")
            return None
    
    async def _save_analytics_record(self, project_id: int, platform: str, analytics_data: Dict, quality_score: float, db: AsyncSession):
        """Save analytics data to the database with quality indicators"""
        try:
            # Check if analytics record already exists for this project and platform
            existing_record = await db.scalar(
                select(PostAnalytics).where(
                    PostAnalytics.project_id == project_id,
                    PostAnalytics.platform == platform
                )
            )
            
            if existing_record:
                # Update existing record
                existing_record.likes = analytics_data.get("likes", 0)
                existing_record.shares = analytics_data.get("shares", 0)
                existing_record.comments = analytics_data.get("comments", 0)
                existing_record.reach = analytics_data.get("reach", 0)
                existing_record.impressions = analytics_data.get("impressions", 0)
                existing_record.clicks = analytics_data.get("clicks", 0)
                existing_record.engagement_rate = analytics_data.get("engagement_rate", 0.0)
                existing_record.click_through_rate = analytics_data.get("click_through_rate", 0.0)
                existing_record.post_url = analytics_data.get("post_url")
                existing_record.data_quality_score = quality_score
                existing_record.last_verified = datetime.utcnow()
                existing_record.updated_at = datetime.utcnow()
                existing_record.last_synced = datetime.utcnow()
            else:
                # Create new record
                new_record = PostAnalytics(
                    post_id=None,  # No post_id for project-level analytics
                    project_id=project_id,
                    platform=platform,
                    post_url=analytics_data.get("post_url"),
                    likes=analytics_data.get("likes", 0),
                    shares=analytics_data.get("shares", 0),
                    comments=analytics_data.get("comments", 0),
                    reach=analytics_data.get("reach", 0),
                    impressions=analytics_data.get("impressions", 0),
                    clicks=analytics_data.get("clicks", 0),
                    engagement_rate=analytics_data.get("engagement_rate", 0.0),
                    click_through_rate=analytics_data.get("click_through_rate", 0.0),
                    ab_test_id=None,
                    variant=None,
                    data_quality_score=quality_score,
                    last_verified=datetime.utcnow(),
                    last_synced=datetime.utcnow()
                )
                db.add(new_record)
            
            await db.commit()
            logger.info(f"Analytics data saved for project {project_id}, platform {platform} (quality: {quality_score})")
            
        except Exception as e:
            logger.error(f"Error saving analytics record: {str(e)}")
            await db.rollback()
            raise
    
    async def _update_analytics_trends(self, project_id: int, db: AsyncSession):
        """Update analytics trends for the project"""
        try:
            # Get recent analytics data
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            
            analytics_query = select(PostAnalytics).where(
                PostAnalytics.project_id == project_id,
                PostAnalytics.created_at >= start_date
            )
            result = await db.execute(analytics_query)
            analytics_data = result.scalars().all()
            
            if not analytics_data:
                return
            
            # Group by platform and calculate trends
            platform_data = {}
            for analytics in analytics_data:
                platform = analytics.platform
                if platform not in platform_data:
                    platform_data[platform] = []
                platform_data[platform].append(analytics)
            
            # Create trend records
            for platform, data in platform_data.items():
                total_posts = len(data)
                total_engagement = sum(a.likes + a.shares + a.comments for a in data)
                total_reach = sum(a.reach for a in data)
                total_impressions = sum(a.impressions for a in data)
                avg_engagement_rate = sum(a.engagement_rate for a in data) / len(data) if data else 0
                avg_click_rate = sum(a.click_through_rate for a in data) / len(data) if data else 0
                
                # Calculate growth (simplified - would need historical data for real growth)
                engagement_growth = 0.0  # Placeholder
                reach_growth = 0.0  # Placeholder
                follower_growth = 0.0  # Placeholder
                
                trend_record = AnalyticsTrend(
                    project_id=project_id,
                    platform=platform,
                    trend_date=end_date,
                    period="monthly",
                    total_posts=total_posts,
                    total_engagement=total_engagement,
                    total_reach=total_reach,
                    total_impressions=total_impressions,
                    avg_engagement_rate=avg_engagement_rate,
                    avg_click_rate=avg_click_rate,
                    engagement_growth=engagement_growth,
                    reach_growth=reach_growth,
                    follower_growth=follower_growth
                )
                
                db.add(trend_record)
            
            await db.commit()
            logger.info(f"Updated analytics trends for project {project_id}")
            
        except Exception as e:
            logger.error(f"Error updating analytics trends: {str(e)}")
            await db.rollback()
    
    async def _generate_insight(self, project_id: int, platform: str, analytics_data: Dict, db: AsyncSession) -> Optional[AnalyticsInsight]:
        """Generate actionable insights from analytics data"""
        try:
            insights = []
            
            # Check for high engagement
            engagement_rate = analytics_data.get("engagement_rate", 0)
            if engagement_rate > 10:
                insights.append({
                    "title": "High Engagement Rate",
                    "description": f"Your {platform} post achieved {engagement_rate:.1f}% engagement rate, which is above average.",
                    "severity": "info",
                    "confidence": 0.9,
                    "recommendations": {
                        "actions": ["Analyze what made this post successful", "Consider similar content for future posts"],
                        "timing": "immediate"
                    }
                })
            
            # Check for low engagement
            elif engagement_rate < 1:
                insights.append({
                    "title": "Low Engagement Rate",
                    "description": f"Your {platform} post has only {engagement_rate:.1f}% engagement rate.",
                    "severity": "warning",
                    "confidence": 0.8,
                    "recommendations": {
                        "actions": ["Review post timing", "Check content quality", "Consider different hashtags"],
                        "timing": "immediate"
                    }
                })
            
            # Check for viral potential
            shares = analytics_data.get("shares", 0)
            if shares > analytics_data.get("likes", 0) * 0.5:
                insights.append({
                    "title": "High Share Rate",
                    "description": f"Your {platform} post has high share rate ({shares} shares), indicating viral potential.",
                    "severity": "info",
                    "confidence": 0.85,
                    "recommendations": {
                        "actions": ["Leverage this content for other platforms", "Create similar shareable content"],
                        "timing": "immediate"
                    }
                })
            
            if insights:
                # Create insight record
                insight = insights[0]  # Take the first insight for now
                insight_record = AnalyticsInsight(
                    project_id=project_id,
                    insight_type="performance",
                    title=insight["title"],
                    description=insight["description"],
                    severity=insight["severity"],
                    confidence=insight["confidence"],
                    data_points=analytics_data,
                    recommendations=insight["recommendations"]
                )
                
                db.add(insight_record)
                await db.commit()
                
                logger.info(f"Generated insight for project {project_id}, platform {platform}")
                return insight_record
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating insight: {str(e)}")
            return None
    
    async def sync_all_projects_analytics(self, db: AsyncSession) -> Dict[str, Any]:
        """Sync analytics for all projects"""
        try:
            # Get all projects
            projects_result = await db.execute(select(Project))
            projects = projects_result.scalars().all()
            
            results = {}
            total_insights = 0
            
            for project in projects:
                project_result = await self.sync_project_analytics(project.id, db)
                results[project.id] = project_result
                
                if "insights_generated" in project_result:
                    total_insights += project_result["insights_generated"]
            
            return {
                "total_projects": len(projects),
                "total_insights_generated": total_insights,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in sync_all_projects_analytics: {str(e)}")
            return {"error": str(e)} 