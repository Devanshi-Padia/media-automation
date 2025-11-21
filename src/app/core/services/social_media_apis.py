import requests
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class TwitterAPI:
    """Twitter/X API v2 integration for analytics"""
    
    def __init__(self, api_key: str, api_secret: str, access_token: str, access_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_secret = access_secret
        self.base_url = "https://api.twitter.com/2"
        self.bearer_token = None
        
    def _get_bearer_token(self) -> Optional[str]:
        """Get bearer token for API authentication"""
        try:
            auth_url = "https://api.twitter.com/oauth2/token"
            auth_data = {
                'grant_type': 'client_credentials'
            }
            auth_response = requests.post(
                auth_url,
                auth=(self.api_key, self.api_secret),
                data=auth_data
            )
            
            if auth_response.status_code == 200:
                token_data = auth_response.json()
                return token_data.get('access_token')
            else:
                logger.error(f"Failed to get Twitter bearer token: {auth_response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting Twitter bearer token: {str(e)}")
            return None
    
    def get_tweet_analytics(self, tweet_id: str) -> Optional[Dict]:
        """Get analytics for a specific tweet"""
        try:
            if not self.bearer_token:
                self.bearer_token = self._get_bearer_token()
                if not self.bearer_token:
                    return None
            
            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json'
            }
            
            # Get tweet metrics
            metrics_url = f"{self.base_url}/tweets/{tweet_id}?tweet.fields=public_metrics,non_public_metrics"
            response = requests.get(metrics_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                tweet = data.get('data', {})
                metrics = tweet.get('public_metrics', {})
                
                # Calculate engagement rate
                impressions = metrics.get('impression_count', 0)
                likes = metrics.get('like_count', 0)
                retweets = metrics.get('retweet_count', 0)
                replies = metrics.get('reply_count', 0)
                
                engagement_rate = 0.0
                if impressions > 0:
                    engagement_rate = ((likes + retweets + replies) / impressions) * 100
                
                return {
                    "likes": likes,
                    "shares": retweets,
                    "comments": replies,
                    "reach": impressions,  # Using impressions as reach
                    "impressions": impressions,
                    "clicks": 0,  # Twitter doesn't provide click data in basic API
                    "engagement_rate": round(engagement_rate, 2),
                    "click_through_rate": 0.0,
                    "post_url": f"https://twitter.com/user/status/{tweet_id}"
                }
            else:
                logger.error(f"Failed to get Twitter analytics: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Twitter analytics: {str(e)}")
            return None

class FacebookAPI:
    """Facebook Graph API integration for analytics"""
    
    def __init__(self, page_id: str, access_token: str):
        self.page_id = page_id
        self.access_token = access_token
        self.base_url = "https://graph.facebook.com/v18.0"
    
    def get_post_analytics(self, post_id: str) -> Optional[Dict]:
        """Get analytics for a specific Facebook post"""
        try:
            # Get post insights
            insights_url = f"{self.base_url}/{post_id}/insights"
            params = {
                'access_token': self.access_token,
                'metric': 'post_impressions,post_reach,post_engaged_users,post_reactions_by_type_total'
            }
            
            response = requests.get(insights_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                insights = data.get('data', [])
                
                # Parse insights
                impressions = 0
                reach = 0
                engagement = 0
                reactions = 0
                
                for insight in insights:
                    metric = insight.get('name')
                    value = insight.get('values', [{}])[0].get('value', 0)
                    
                    if metric == 'post_impressions':
                        impressions = value
                    elif metric == 'post_reach':
                        reach = value
                    elif metric == 'post_engaged_users':
                        engagement = value
                    elif metric == 'post_reactions_by_type_total':
                        reactions = value
                
                # Calculate engagement rate
                engagement_rate = 0.0
                if reach > 0:
                    engagement_rate = (engagement / reach) * 100
                
                return {
                    "likes": reactions,
                    "shares": 0,  # Facebook doesn't provide shares in basic API
                    "comments": 0,  # Would need separate API call
                    "reach": reach,
                    "impressions": impressions,
                    "clicks": 0,
                    "engagement_rate": round(engagement_rate, 2),
                    "click_through_rate": 0.0,
                    "post_url": f"https://facebook.com/{post_id}"
                }
            else:
                logger.error(f"Failed to get Facebook analytics: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Facebook analytics: {str(e)}")
            return None

class InstagramAPI:
    """Instagram Basic Display API integration for analytics"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.instagram.com/v12.0"
    
    def get_post_analytics(self, post_id: str) -> Optional[Dict]:
        """Get analytics for a specific Instagram post"""
        try:
            # Instagram Basic Display API has very limited analytics
            # For better analytics, you'd need Instagram Graph API
            post_url = f"{self.base_url}/{post_id}"
            params = {
                'access_token': self.access_token,
                'fields': 'id,media_type,media_url,permalink,timestamp'
            }
            
            response = requests.get(post_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Instagram Basic Display API doesn't provide engagement metrics
                # This is a limitation - you'd need Instagram Graph API for real analytics
                return {
                    "likes": 0,  # Not available in Basic Display API
                    "shares": 0,
                    "comments": 0,
                    "reach": 0,
                    "impressions": 0,
                    "clicks": 0,
                    "engagement_rate": 0.0,
                    "click_through_rate": 0.0,
                    "post_url": data.get('permalink', f"https://instagram.com/p/{post_id}")
                }
            else:
                logger.error(f"Failed to get Instagram analytics: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Instagram analytics: {str(e)}")
            return None

class LinkedInAPI:
    """LinkedIn API integration for analytics"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.linkedin.com/v2"
    
    def get_post_analytics(self, post_id: str) -> Optional[Dict]:
        """Get analytics for a specific LinkedIn post"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # LinkedIn API requires specific permissions for analytics
            # This is a simplified implementation
            analytics_url = f"{self.base_url}/socialMetrics/{post_id}"
            response = requests.get(analytics_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse LinkedIn analytics (structure may vary)
                likes = data.get('totalShareStatistics', {}).get('likes', 0)
                shares = data.get('totalShareStatistics', {}).get('shares', 0)
                comments = data.get('totalShareStatistics', {}).get('comments', 0)
                impressions = data.get('impressions', 0)
                
                # Calculate engagement rate
                engagement_rate = 0.0
                if impressions > 0:
                    engagement_rate = ((likes + shares + comments) / impressions) * 100
                
                return {
                    "likes": likes,
                    "shares": shares,
                    "comments": comments,
                    "reach": impressions,
                    "impressions": impressions,
                    "clicks": 0,
                    "engagement_rate": round(engagement_rate, 2),
                    "click_through_rate": 0.0,
                    "post_url": f"https://linkedin.com/posts/{post_id}"
                }
            else:
                logger.error(f"Failed to get LinkedIn analytics: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting LinkedIn analytics: {str(e)}")
            return None

class DiscordAPI:
    """Discord API integration for analytics"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.base_url = "https://discord.com/api/v10"
    
    def get_message_analytics(self, message_id: str) -> Optional[Dict]:
        """Get analytics for a specific Discord message"""
        try:
            # Discord doesn't provide public analytics API
            # This would require custom implementation with bot permissions
            # For now, return basic structure
            
            return {
                "likes": 0,  # Discord doesn't have likes
                "shares": 0,
                "comments": 0,  # Would need to count reactions
                "reach": 0,  # Would need channel member count
                "impressions": 0,
                "clicks": 0,
                "engagement_rate": 0.0,
                "click_through_rate": 0.0,
                "post_url": f"https://discord.com/channels/{message_id}"
            }
                
        except Exception as e:
            logger.error(f"Error getting Discord analytics: {str(e)}")
            return None

class TelegramAPI:
    """Telegram Bot API integration for analytics"""
    
    def __init__(self, bot_token: str, channel_id: str):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def get_message_analytics(self, message_id: str) -> Optional[Dict]:
        """Get analytics for a specific Telegram message"""
        try:
            # Telegram doesn't provide public analytics API
            # This would require custom implementation with bot permissions
            # For now, return basic structure
            
            return {
                "likes": 0,  # Telegram doesn't have likes
                "shares": 0,
                "comments": 0,  # Would need to count reactions
                "reach": 0,  # Would need channel member count
                "impressions": 0,
                "clicks": 0,
                "engagement_rate": 0.0,
                "click_through_rate": 0.0,
                "post_url": f"https://t.me/{self.channel_id}/{message_id}"
            }
                
        except Exception as e:
            logger.error(f"Error getting Telegram analytics: {str(e)}")
            return None 