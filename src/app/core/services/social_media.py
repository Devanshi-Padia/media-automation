import os
import logging
import tweepy
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from PIL import Image
from typing import Dict, Any, Optional
import glob
import errno
import shutil
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def onerror(func, path, exc_info):
    """Handle errors during directory removal, especially on Windows where files may be locked."""
    import stat
    error_type, error_instance, traceback = exc_info
    
    # On Windows, files might be locked by another process
    if isinstance(error_instance, PermissionError) or isinstance(error_instance, OSError):
        try:
            # Try to change file permissions and remove
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            # If we still can't delete it, just log and skip
            logger.warning(f"Could not delete {path}, file may be in use. Continuing anyway.")
            pass
    else:
        raise

class SocialMediaService:
    def __init__(self):
        pass  # No credentials or clients stored on the instance

    def resize_image(self, image_path: str, max_size: tuple = (1080, 1080)) -> Optional[str]:
        try:
            with Image.open(image_path) as img:
                img.thumbnail(max_size)
                resized_path = f'{image_path}_resized.jpg'
                img.save(resized_path)
            return resized_path
        except Exception as e:
            logger.error(f"Error resizing image: {e}", exc_info=True)
            return None

    def post_to_telegram(self, text: Dict[str, str], image_path: Optional[str], credentials: Dict[str, str]) -> Optional[Dict]:
        """Post content to Telegram channel"""
        try:
            bot_token = credentials.get('telegram_bot_token')
            chat_id = credentials.get('telegram_chat_id')
            
            if not (bot_token and chat_id):
                logger.warning("Telegram credentials not configured")
                return None

            message = text.get('telegram', '') if isinstance(text, dict) else str(text)
            
            if image_path:
                # Send photo with caption
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                with open(image_path, 'rb') as photo:
                    files = {'photo': photo}
                    data = {
                        'chat_id': chat_id,
                        'caption': message,
                        'parse_mode': 'HTML'  # Support basic HTML formatting
                    }
                    response = requests.post(url, data=data, files=files)
            else:
                # Send text message only
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = {
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, data=data)

            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info('Successfully posted to Telegram')
                    return {"success": True, "message": "Successfully posted to Telegram"}
                else:
                    logger.error(f"Telegram API error: {result}")
                    return None
            else:
                logger.error(f"Error posting to Telegram: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error posting to Telegram: {e}", exc_info=True)
            return None

    def post_to_twitter(self, text: Dict[str, str], image_path: Optional[str], credentials: Dict[str, str]) -> Optional[Any]:
        try:
            import tweepy
            api_key = credentials.get('twitter_api_key')
            api_secret = credentials.get('twitter_api_secret')
            access_token = credentials.get('twitter_access_token')
            access_secret = credentials.get('twitter_access_secret')
            if not all([api_key, api_secret, access_token, access_secret]):
                logger.warning("Twitter credentials not provided")
                return None
            # v1.1 API for media upload
            auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
            twitter_api = tweepy.API(auth)
            # v2 API for tweet posting
            twitter_client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_secret
            )
            # --- Always use JPEG for Twitter ---
            import os
            from PIL import Image
            if image_path and image_path.lower().endswith('.png'):
                jpeg_path = os.path.splitext(image_path)[0] + '.jpg'
                if not os.path.exists(jpeg_path):
                    with Image.open(image_path) as img:
                        img = img.convert('RGB')
                        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                        img.save(jpeg_path, format='JPEG', quality=85)
                image_path = jpeg_path
            # --- End JPEG for Twitter ---
            # --- Always trim text to 280 chars and handle both 'twitter' and 'x' keys ---
            tweet_text = text.get('twitter') or text.get('x') or ''
            tweet_text = tweet_text[:280]

            if image_path:
                try:
                    media = twitter_api.media_upload(image_path)
                    tweet = twitter_client.create_tweet(
                        text=tweet_text,
                        media_ids=[media.media_id]
                    )
                    logger.info('Successfully posted to Twitter with image')
                    return tweet
                except Exception as upload_error:
                    logger.error(f'Twitter media upload error: {upload_error}')
                    # Fallback: post text-only tweet
                    tweet = twitter_client.create_tweet(text=tweet_text)
                    logger.warning('Posted to Twitter without image as a fallback')
                    return tweet
            else:
                # Post text-only tweet
                tweet = twitter_client.create_tweet(text=tweet_text)
                logger.info('Successfully posted to Twitter (text only)')
                return tweet
        except Exception as e:
            logger.error(f"Error posting to Twitter: {e}", exc_info=True)
            return None

    def post_to_instagram(self, text: Dict[str, str], image_path: Optional[str], credentials: Dict[str, str]) -> Optional[Dict]:
        """
        Post an image to Instagram using instabot.
        """
        if not image_path:
            logger.warning("Instagram requires an image to post. Skipping.")
            return None
        try:
            from instabot import Bot
            import shutil
            import os
            import time
            # --- Clean up Instabot config folder before login ---
            config_dir = os.path.join(os.getcwd(), "config")
            if os.path.exists(config_dir):
                try:
                    # Try to remove the config directory
                    shutil.rmtree(config_dir, onerror=onerror)
                except (PermissionError, OSError) as e:
                    # If files are locked, wait a bit and try again
                    logger.warning(f"Config directory cleanup failed (files may be locked): {e}. Retrying...")
                    time.sleep(0.5)
                    try:
                        shutil.rmtree(config_dir, onerror=onerror)
                    except Exception as retry_error:
                        # If still failing, log and continue - instabot should handle existing config
                        logger.warning(f"Could not clean config directory: {retry_error}. Continuing with existing config.")
            # ---------------------------------------------------
            ig_username = credentials.get('ig_username')
            ig_password = credentials.get('ig_password')
            caption = text.get('instagram', '') if isinstance(text, dict) else str(text)
            if not (ig_username and ig_password):
                logger.warning("Instagram username or password not configured")
                return None
            bot = Bot()
            try:
                bot.login(username=ig_username, password=ig_password)
            except SystemExit:
                # instabot calls sys.exit() on login failure, which we need to catch
                logger.error("Instagram login failed: Invalid credentials or account requires Facebook login")
                return None
            except Exception as login_error:
                logger.error(f"Instagram login error: {login_error}")
                return None
            
            # Instabot requires .jpg extension for upload
            if not image_path.lower().endswith('.jpg'):
                from PIL import Image
                img = Image.open(image_path)
                jpg_path = image_path + ".jpg"
                img.convert('RGB').save(jpg_path, "JPEG")
                image_path_to_upload = jpg_path
            else:
                image_path_to_upload = image_path
            # Delete .REMOVE_ME file if it exists before upload
            remove_me_path = image_path_to_upload + ".REMOVE_ME"
            if os.path.exists(remove_me_path):
                os.remove(remove_me_path)
            result = bot.upload_photo(image_path_to_upload, caption=caption)
            if result:
                logger.info('Successfully posted to Instagram via instabot')
                return {"success": True, "message": "Successfully posted to Instagram"}
            else:
                logger.error("Instabot failed to upload photo")
                return None
        except SystemExit:
            # Catch SystemExit that might escape from instabot
            logger.error("Instagram posting failed: SystemExit from instabot (likely login failure)")
            return None
        except Exception as e:
            logger.error(f"Error posting to Instagram via instabot: {e}", exc_info=True)
            return None

    def post_to_linkedin(self, text: Dict[str, str], image_path: Optional[str], credentials: Dict[str, str]) -> Optional[Dict]:
        try:
            access_token = credentials.get('linkedin_access_token')
            author_urn = credentials.get('linkedin_author_urn')
            if not access_token or not author_urn:
                logger.warning("LinkedIn access token or author URN not configured")
                return None
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0'
            }

            post_data = {
                'author': author_urn,
                'lifecycleState': 'PUBLISHED',
                'specificContent': {
                    'com.linkedin.ugc.ShareContent': {
                        'shareCommentary': {'text': text.get('linkedin', '') if isinstance(text, dict) else str(text)},
                        'shareMediaCategory': 'NONE'
                    }
                },
                'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'}
            }

            if image_path:
                upload_url = 'https://api.linkedin.com/v2/assets?action=registerUpload'
                media = {
                    'registerUploadRequest': {
                        'recipes': ['urn:li:digitalmediaRecipe:feedshare-image'],
                        'owner': author_urn,
                        'serviceRelationships': [{
                            'relationshipType': 'OWNER',
                            'identifier': 'urn:li:userGeneratedContent'
                        }]
                    }
                }
                response = requests.post(upload_url, json=media, headers=headers)
                upload_info = response.json()
                upload_http_url = upload_info['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
                asset = upload_info['value']['asset']
                with open(image_path, 'rb') as image_file:
                    requests.put(upload_http_url, data=image_file, headers={'Authorization': f'Bearer {access_token}'})
                
                post_data['specificContent']['com.linkedin.ugc.ShareContent']['shareMediaCategory'] = 'IMAGE'
                post_data['specificContent']['com.linkedin.ugc.ShareContent']['media'] = [{'status': 'READY', 'media': asset}]

            post_url = 'https://api.linkedin.com/v2/ugcPosts'
            post_response = requests.post(post_url, headers=headers, json=post_data)

            if post_response.status_code in (200, 201):
                logger.info('Successfully posted to LinkedIn')
                return post_response.json()
            else:
                logger.error(f"Error posting to LinkedIn: {post_response.text}")
                return None
        except Exception as e:
            logger.error(f"Error posting to LinkedIn: {e}", exc_info=True)
            return None

    def post_to_facebook(self, text: Dict[str, str], image_path: Optional[str], credentials: Dict[str, str]) -> Optional[Dict]:
        try:
            fb_page_id = credentials.get('fb_page_id')
            fb_page_access_token = credentials.get('fb_page_access_token')
            if not (fb_page_id and fb_page_access_token):
                logger.warning("Facebook credentials not configured")
                return None

            message = text.get('facebook', '') if isinstance(text, dict) else str(text)

            if image_path:
                # Post with image
                with open(image_path, 'rb') as img_file:
                    files = {'source': img_file}
                    data = {'message': message, 'access_token': fb_page_access_token}
                    response = requests.post(f'https://graph.facebook.com/v18.0/{fb_page_id}/photos', data=data, files=files)
            else:
                # Post text only
                data = {'message': message, 'access_token': fb_page_access_token}
                response = requests.post(f'https://graph.facebook.com/v18.0/{fb_page_id}/feed', data=data)

            if response.status_code == 200:
                logger.info('Successfully posted to Facebook')
                return response.json()
            else:
                logger.error(f"Error posting to Facebook: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error posting to Facebook: {e}", exc_info=True)
            return None

    def post_to_discord(self, text: Dict[str, str], image_path: Optional[str], credentials: Dict[str, str]) -> Optional[Dict]:
        try:
            discord_webhook_url = credentials.get('discord_webhook_url')
            if not discord_webhook_url:
                logger.warning("Discord webhook URL not configured")
                return None

            message = text.get('discord', '') if isinstance(text, dict) else str(text)

            if image_path:
                with open(image_path, 'rb') as img_file:
                    m = MultipartEncoder(
                        fields={
                            'content': message,
                            'file': (os.path.basename(image_path), img_file, 'image/jpeg')
                        }
                    )
                    response = requests.post(discord_webhook_url, data=m, headers={'Content-Type': m.content_type})
            else:
                response = requests.post(discord_webhook_url, json={'content': message})

            if response.status_code in (200, 204):  # 204 is no content (success)
                logger.info('Successfully posted to Discord')
                if response.content:
                    return response.json()
                return {"success": True, "message": "Successfully posted to Discord"}
            else:
                logger.error(f"Error posting to Discord: {response.text}")
                return None
        except requests.exceptions.MissingSchema as e:
            logger.error(f"Invalid Discord webhook URL: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Discord request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error posting to Discord: {e}", exc_info=True)
            return None

    def post_to_social_media(self, text: Dict[str, str], image_path: Optional[str], credentials_map: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        try:
            if image_path and not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found at path: {image_path}")

            logger.info('Posting content to social media platforms...')
            # print(f"[DEBUG] Text payload: {text}")
            # print(f"[DEBUG] Image path: {image_path}")
            # print(f"[DEBUG] Credentials map: {credentials_map}")
            
            results = {}
            responses = {'success': [], 'failures': []}
            # Only post to platforms that are present in credentials_map
            for platform, creds in credentials_map.items():
                platform_lower = platform.lower()
                if platform_lower == 'twitter' or platform_lower == 'x':
                    result = self.post_to_twitter(text, image_path, creds)
                elif platform_lower == 'instagram':
                    result = self.post_to_instagram(text, image_path, creds)
                elif platform_lower == 'linkedin':
                    result = self.post_to_linkedin(text, image_path, creds)
                elif platform_lower == 'facebook':
                    result = self.post_to_facebook(text, image_path, creds)
                elif platform_lower == 'discord':
                    result = self.post_to_discord(text, image_path, creds)
                elif platform_lower == 'telegram':
                    result = self.post_to_telegram(text, image_path, creds)
                else:
                    continue
                results[platform.capitalize()] = result
                # Check if result exists and indicates successful post
                success = False
                if result is not None:
                    if isinstance(result, dict):
                        # Check for success indicators in dict responses
                        if result.get('success') is True:
                            success = True
                        elif 'id' in result:  # LinkedIn/Facebook response
                            success = True
                        elif 'message' in result and 'Successfully posted' in result.get('message', ''):  # Discord success
                            success = True
                    elif hasattr(result, 'data'):  # Twitter response object
                        success = True
                
                if success:
                    responses['success'].append(platform.capitalize())
                else:
                    responses['failures'].append(platform.capitalize())
            if not responses['failures']:
                return {
                    'status': 'posted',
                    'message': 'Post published successfully!',
                    'successful_platforms': responses['success'],
                    'failed_platforms': responses['failures']
                }
            else:
                return {
                    'status': 'partial',
                    'message': 'Post published to some platforms, but failed for others.',
                    'successful_platforms': responses['success'],
                    'failed_platforms': responses['failures']
                }
        except Exception as e:
            logger.error(f"Error in post_to_social_media: {e}", exc_info=True)
            return {'status': 'failure', 'error': str(e)}

    async def get_post_analytics(self, post_id: int, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get analytics data for a post from a specific platform
        This method should be implemented to call actual platform APIs
        """
        try:
            # This method should be implemented to fetch real analytics from platform APIs
            logger.warning(f"get_post_analytics not implemented for platform {platform}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting analytics for post {post_id} on {platform}: {e}", exc_info=True)
            return None

    async def get_facebook_analytics(self, post_id: str, access_token: str) -> Optional[Dict[str, Any]]:
        """Get Facebook post analytics using Graph API"""
        try:
            url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
            params = {
                'access_token': access_token,
                'metric': 'post_impressions,post_reach,post_engagement,post_clicks'
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                # Process the data and return formatted analytics
                return self._process_facebook_analytics(data)
            else:
                logger.error(f"Facebook API error: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Facebook analytics: {e}", exc_info=True)
            return None

    async def get_twitter_analytics(self, tweet_id: str, credentials: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Get Twitter post analytics using Twitter API v2"""
        try:
            # This method should be implemented to fetch real analytics from Twitter API v2
            logger.warning("get_twitter_analytics not implemented")
            return None
            
        except Exception as e:
            logger.error(f"Error getting Twitter analytics: {e}", exc_info=True)
            return None

    def _process_facebook_analytics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Facebook analytics data"""
        try:
            insights = data.get('data', [])
            analytics = {
                "likes": 0,
                "shares": 0,
                "comments": 0,
                "reach": 0,
                "impressions": 0,
                "clicks": 0
            }
            
            for insight in insights:
                metric = insight.get('name', '')
                value = insight.get('values', [{}])[0].get('value', 0)
                
                if metric == 'post_impressions':
                    analytics['impressions'] = value
                elif metric == 'post_reach':
                    analytics['reach'] = value
                elif metric == 'post_engagement':
                    analytics['likes'] = value
                elif metric == 'post_clicks':
                    analytics['clicks'] = value
            
            # Calculate engagement rate
            if analytics['reach'] > 0:
                analytics['engagement_rate'] = round((analytics['likes'] / analytics['reach']) * 100, 2)
            else:
                analytics['engagement_rate'] = 0.0
                
            # Calculate click-through rate
            if analytics['impressions'] > 0:
                analytics['click_through_rate'] = round((analytics['clicks'] / analytics['impressions']) * 100, 2)
            else:
                analytics['click_through_rate'] = 0.0
                
            return analytics
            
        except Exception as e:
            logger.error(f"Error processing Facebook analytics: {e}", exc_info=True)
            return {}
