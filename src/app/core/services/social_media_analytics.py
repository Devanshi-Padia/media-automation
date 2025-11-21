import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...models.analytics import PostAnalytics
from ...models.project import Project, SocialMediaCredential
from ...models.post import Post


class SocialMediaAnalyticsService:
    """Service to fetch real analytics data from social media platforms"""
    
    def __init__(self):
        self.session_timeout = aiohttp.ClientTimeout(total=30)
    
    async def fetch_facebook_analytics(self, access_token: str, project_id: str) -> Dict[str, Any]:
        """Fetch Facebook project analytics"""
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                # For project-level analytics, we need to get the page ID first
                # Then fetch page-level insights
                url = "https://graph.facebook.com/v18.0/me"
                params = {
                    'access_token': access_token,
                    'fields': 'id,name'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        page_data = await response.json()
                        page_id = page_data.get('id')
                        
                        if page_id:
                            # Fetch page insights
                            insights_url = f"https://graph.facebook.com/v18.0/{page_id}/insights"
                            insights_params = {
                                'access_token': access_token,
                                'metric': 'page_impressions,page_reach,page_engagement,page_fans'
                            }
                            
                            async with session.get(insights_url, params=insights_params) as insights_response:
                                if insights_response.status == 200:
                                    data = await insights_response.json()
                                    return self._parse_facebook_metrics(data)
                                else:
                                    print(f"Facebook insights API error: {insights_response.status}")
                                    return self._get_default_metrics()
                        else:
                            print("Could not get Facebook page ID")
                            return self._get_default_metrics()
                    else:
                        print(f"Facebook API error: {response.status}")
                        return self._get_default_metrics()
        except Exception as e:
            print(f"Error fetching Facebook analytics: {e}")
            return self._get_default_metrics()
    
    async def fetch_instagram_analytics(self, access_token: str, project_id: str) -> Dict[str, Any]:
        """Fetch Instagram project analytics"""
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                # For Instagram, we need to get the business account ID first
                url = "https://graph.facebook.com/v18.0/me/accounts"
                params = {
                    'access_token': access_token,
                    'fields': 'instagram_business_account'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        accounts_data = await response.json()
                        if 'data' in accounts_data and accounts_data['data']:
                            # Get the first account with Instagram business account
                            for account in accounts_data['data']:
                                if 'instagram_business_account' in account:
                                    ig_account_id = account['instagram_business_account']['id']
                                    
                                    # Fetch Instagram business account insights
                                    insights_url = f"https://graph.facebook.com/v18.0/{ig_account_id}/insights"
                                    insights_params = {
                                        'access_token': access_token,
                                        'metric': 'impressions,reach,profile_views,follower_count'
                                    }
                                    
                                    async with session.get(insights_url, params=insights_params) as insights_response:
                                        if insights_response.status == 200:
                                            data = await insights_response.json()
                                            return self._parse_instagram_metrics(data)
                                        else:
                                            print(f"Instagram insights API error: {insights_response.status}")
                                            return self._get_default_metrics()
                            
                            print("No Instagram business account found")
                            return self._get_default_metrics()
                        else:
                            print("No Facebook accounts found")
                            return self._get_default_metrics()
                    else:
                        print(f"Instagram API error: {response.status}")
                        return self._get_default_metrics()
        except Exception as e:
            print(f"Error fetching Instagram analytics: {e}")
            return self._get_default_metrics()
    
    async def fetch_twitter_analytics(self, access_token: str, project_id: str) -> Dict[str, Any]:
        """Fetch Twitter project analytics"""
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                # For Twitter, we need to get user metrics
                url = "https://api.twitter.com/2/users/me"
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        user_id = user_data.get('data', {}).get('id')
                        
                        if user_id:
                            # Fetch user metrics
                            metrics_url = f"https://api.twitter.com/2/users/{user_id}"
                            metrics_params = {
                                'user.fields': 'public_metrics'
                            }
                            
                            async with session.get(metrics_url, headers=headers, params=metrics_params) as metrics_response:
                                if metrics_response.status == 200:
                                    data = await metrics_response.json()
                                    return self._parse_twitter_metrics(data)
                                else:
                                    print(f"Twitter metrics API error: {metrics_response.status}")
                                    return self._get_default_metrics()
                        else:
                            print("Could not get Twitter user ID")
                            return self._get_default_metrics()
                    else:
                        print(f"Twitter API error: {response.status}")
                        return self._get_default_metrics()
        except Exception as e:
            print(f"Error fetching Twitter analytics: {e}")
            return self._get_default_metrics()
    
    async def fetch_linkedin_analytics(self, access_token: str, project_id: str) -> Dict[str, Any]:
        """Fetch LinkedIn project analytics"""
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                # For LinkedIn, we need to get organization analytics
                url = "https://api.linkedin.com/v2/organizationalEntityShareStatistics"
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_linkedin_metrics(data)
                    else:
                        print(f"LinkedIn API error: {response.status}")
                        return self._get_default_metrics()
        except Exception as e:
            print(f"Error fetching LinkedIn analytics: {e}")
            return self._get_default_metrics()
    
    async def fetch_discord_analytics(self, webhook_url: str, project_id: str) -> Dict[str, Any]:
        """Fetch Discord server analytics"""
        try:
            # Discord webhooks don't provide analytics, but we can track basic metrics
            # This would require using the Discord API instead of webhook
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                # For Discord, we might need to use the Discord API instead of webhook
                # This is a simplified implementation
                return {
                    'likes': 0,  # Discord doesn't have likes
                    'shares': 0,  # Discord doesn't have shares
                    'comments': 0,  # Could track reactions
                    'reach': 0,  # Could track channel member count
                    'impressions': 0,
                    'clicks': 0,
                    'engagement': 0,
                    'engagement_rate': 0.0,
                    'click_through_rate': 0.0
                }
        except Exception as e:
            print(f"Error fetching Discord analytics: {e}")
            return self._get_default_metrics()
    
    async def fetch_telegram_analytics(self, bot_token: str, project_id: str) -> Dict[str, Any]:
        """Fetch Telegram channel analytics"""
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                # Telegram Bot API doesn't provide message analytics
                # This would require storing message IDs when posts are sent
                url = f"https://api.telegram.org/bot{bot_token}/getChat"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        # For now, return basic metrics
                        return {
                            'likes': 0,  # Telegram doesn't have likes
                            'shares': 0,  # Could track forwards
                            'comments': 0,  # Could track replies
                            'reach': 0,  # Could track channel member count
                            'impressions': 0,
                            'clicks': 0,
                            'engagement': 0,
                            'engagement_rate': 0.0,
                            'click_through_rate': 0.0
                        }
                    else:
                        print(f"Telegram API error: {response.status}")
                        return self._get_default_metrics()
        except Exception as e:
            print(f"Error fetching Telegram analytics: {e}")
            return self._get_default_metrics()
    
    def _parse_facebook_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Facebook API response"""
        metrics = self._get_default_metrics()
        
        if 'data' in data:
            for metric in data['data']:
                if metric['name'] == 'post_impressions':
                    metrics['impressions'] = metric.get('values', [{}])[0].get('value', 0)
                elif metric['name'] == 'post_reach':
                    metrics['reach'] = metric.get('values', [{}])[0].get('value', 0)
                elif metric['name'] == 'post_engagement':
                    metrics['engagement'] = metric.get('values', [{}])[0].get('value', 0)
        
        return metrics
    
    def _parse_instagram_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Instagram API response"""
        metrics = self._get_default_metrics()
        
        if 'data' in data:
            for metric in data['data']:
                if metric['name'] == 'impressions':
                    metrics['impressions'] = metric.get('values', [{}])[0].get('value', 0)
                elif metric['name'] == 'reach':
                    metrics['reach'] = metric.get('values', [{}])[0].get('value', 0)
                elif metric['name'] == 'engagement':
                    metrics['engagement'] = metric.get('values', [{}])[0].get('value', 0)
        
        return metrics
    
    def _parse_twitter_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Twitter API response"""
        metrics = self._get_default_metrics()
        
        if 'data' in data:
            tweet_data = data['data']
            metrics['impressions'] = tweet_data.get('impression_count', 0)
            metrics['likes'] = tweet_data.get('like_count', 0)
            metrics['retweets'] = tweet_data.get('retweet_count', 0)
            metrics['replies'] = tweet_data.get('reply_count', 0)
            metrics['engagement'] = metrics['likes'] + metrics['retweets'] + metrics['replies']
        
        return metrics
    
    def _parse_linkedin_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LinkedIn API response"""
        metrics = self._get_default_metrics()
        
        # LinkedIn metrics structure may vary
        metrics['impressions'] = data.get('impressions', 0)
        metrics['likes'] = data.get('likes', 0)
        metrics['comments'] = data.get('comments', 0)
        metrics['shares'] = data.get('shares', 0)
        metrics['engagement'] = metrics['likes'] + metrics['comments'] + metrics['shares']
        
        return metrics
    
    def _get_default_metrics(self) -> Dict[str, Any]:
        """Return default metrics structure"""
        return {
            'likes': 0,
            'shares': 0,
            'comments': 0,
            'reach': 0,
            'impressions': 0,
            'clicks': 0,
            'engagement': 0,
            'engagement_rate': 0.0,
            'click_through_rate': 0.0
        }
    
    async def sync_project_analytics(self, db: AsyncSession, project_id: int) -> Dict[str, Any]:
        """Sync analytics for a project"""
        try:
            # Get project and its social credentials
            query = select(Project).where(Project.id == project_id)
            result = await db.execute(query)
            project = result.scalar_one_or_none()
            
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Get social credentials for the project
            credentials_query = select(SocialMediaCredential).where(
                SocialMediaCredential.project_id == project_id
            )
            credentials_result = await db.execute(credentials_query)
            credentials = credentials_result.scalars().all()
            
            if not credentials:
                return {
                    "success": False,
                    "error": "No social media credentials found for this project"
                }
            
            # Create credentials lookup
            creds_lookup = {cred.platform: cred for cred in credentials}
            
            synced_count = 0
            errors = []
            
            # For each platform with credentials, fetch project-level analytics
            for platform, cred in creds_lookup.items():
                try:
                    # Fetch analytics for this platform at project level
                    analytics = await self._fetch_platform_analytics(
                        platform, cred, str(project_id)  # Use project_id as identifier
                    )
                    
                    # Save to database
                    await self._save_analytics(db, project_id, None, platform, analytics)
                    synced_count += 1
                
                except Exception as e:
                    errors.append(f"Error syncing {platform}: {str(e)}")
            
            return {
                "success": True,
                "synced_count": synced_count,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    

    
    async def _fetch_platform_analytics(self, platform: str, credentials: SocialMediaCredential, project_id: str) -> Dict[str, Any]:
        """Fetch analytics for a specific platform"""
        try:
            if platform == 'facebook':
                if not credentials.fb_page_access_token:
                    print(f"No Facebook access token for project {project_id}")
                    return self._get_default_metrics()
                return await self.fetch_facebook_analytics(credentials.fb_page_access_token, project_id)
            elif platform == 'instagram':
                if not credentials.fb_page_access_token:
                    print(f"No Facebook access token for Instagram project {project_id}")
                    return self._get_default_metrics()
                return await self.fetch_instagram_analytics(credentials.fb_page_access_token, project_id)  # Instagram uses Facebook token
            elif platform == 'twitter':
                if not credentials.twitter_access_token:
                    print(f"No Twitter access token for project {project_id}")
                    return self._get_default_metrics()
                return await self.fetch_twitter_analytics(credentials.twitter_access_token, project_id)
            elif platform == 'linkedin':
                if not credentials.linkedin_access_token:
                    print(f"No LinkedIn access token for project {project_id}")
                    return self._get_default_metrics()
                return await self.fetch_linkedin_analytics(credentials.linkedin_access_token, project_id)
            elif platform == 'discord':
                if not credentials.discord_webhook_url:
                    print(f"No Discord webhook URL for project {project_id}")
                    return self._get_default_metrics()
                return await self.fetch_discord_analytics(credentials.discord_webhook_url, project_id)
            elif platform == 'telegram':
                if not credentials.telegram_bot_token:
                    print(f"No Telegram bot token for project {project_id}")
                    return self._get_default_metrics()
                return await self.fetch_telegram_analytics(credentials.telegram_bot_token, project_id)
            else:
                print(f"Unknown platform: {platform}")
                return self._get_default_metrics()
        except Exception as e:
            print(f"Error fetching {platform} analytics: {str(e)}")
            return self._get_default_metrics()
    
    async def _save_analytics(self, db: AsyncSession, project_id: int, post_id: int | None, platform: str, analytics: Dict[str, Any]):
        """Save analytics data to database"""
        # Check if analytics record already exists
        query = select(PostAnalytics).where(
            PostAnalytics.project_id == project_id,
            PostAnalytics.platform == platform
        )
        if post_id:
            query = query.where(PostAnalytics.post_id == post_id)
        else:
            query = query.where(PostAnalytics.post_id.is_(None))
            
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing record
            existing.likes = analytics['likes']
            existing.shares = analytics['shares']
            existing.comments = analytics['comments']
            existing.reach = analytics['reach']
            existing.impressions = analytics['impressions']
            existing.clicks = analytics['clicks']
            existing.engagement_rate = analytics['engagement_rate']
            existing.click_through_rate = analytics['click_through_rate']
            existing.updated_at = datetime.utcnow()
            existing.last_synced = datetime.utcnow()
        else:
            # Create new record
            new_analytics = PostAnalytics(
                project_id=project_id,
                post_id=post_id,  # Can be None for project-level analytics
                platform=platform,
                likes=analytics['likes'],
                shares=analytics['shares'],
                comments=analytics['comments'],
                reach=analytics['reach'],
                impressions=analytics['impressions'],
                clicks=analytics['clicks'],
                engagement_rate=analytics['engagement_rate'],
                click_through_rate=analytics['click_through_rate'],
                last_synced=datetime.utcnow()
            )
            db.add(new_analytics)
        
        await db.commit()


# Global instance
social_media_analytics_service = SocialMediaAnalyticsService()
