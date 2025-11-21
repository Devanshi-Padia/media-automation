# Content Generation

This guide explains how to use the content generation features integrated into the FastAPI boilerplate.

## Overview

The content generation system provides:
- **Text Generation**: AI-powered content creation for multiple social media platforms
- **Image Generation**: DALL-E 3 powered image generation with custom templates
- **Social Media Integration**: Automated posting to Twitter, Instagram, LinkedIn, Facebook, and Discord
- **News Integration**: Real-time blockchain news fetching and content creation

## Features

### 1. Text Generation Service
- Generates platform-specific content (Twitter, Instagram, Facebook, LinkedIn, Discord)
- Automatically trims content to platform character limits
- Includes trending hashtags and emojis
- Integrates with latest blockchain news

### 2. Image Generation Service
- Uses DALL-E 3 for high-quality image generation
- Applies custom templates with headlines and text overlays
- Supports image compression for social media platforms
- Automatic retry mechanism for failed generations

### 3. Social Media Service
- Multi-platform posting (Twitter, Instagram, LinkedIn, Facebook, Discord)
- Automatic image resizing for platform requirements
- Error handling and success tracking
- Configurable platform selection

## API Endpoints

### Generate Content
```http
POST /api/v1/content/generate
```

**Request Body:**
```json
{
  "prompt": "Your content prompt here",
  "include_news": true,
  "platforms": ["twitter", "instagram", "linkedin"]
}
```

**Response:**
```json
{
  "text": {
    "twitter": "Generated Twitter content...",
    "instagram": "Generated Instagram content...",
    "linkedin": "Generated LinkedIn content..."
  },
  "image_path": "/api/v1/content/image/generated_1234567890.png",
  "prompt": "Your content prompt here"
}
```

### Post to Social Media
```http
POST /api/v1/content/post-to-social-media
```

**Request Body:**
```json
{
  "text": {
    "twitter": "Content for Twitter",
    "instagram": "Content for Instagram"
  },
  "image_path": "/path/to/image.png",
  "platforms": ["twitter", "instagram"]
}
```

### Get Generated Image
```http
GET /api/v1/content/image/{filename}
```

Returns the generated image file.

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# News API
NEWS_API_KEY=your_news_api_key_here

# Twitter API
TWITTER_API_KEY=your_twitter_api_key_here
TWITTER_API_SECRET=your_twitter_api_secret_here
TWITTER_ACCESS_TOKEN=your_twitter_access_token_here
TWITTER_ACCESS_SECRET=your_twitter_access_secret_here

# Instagram
IG_USERNAME=your_instagram_username_here
IG_PASSWORD=your_instagram_password_here

# LinkedIn
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token_here

# Facebook
FB_PAGE_ID=your_facebook_page_id_here
FB_PAGE_ACCESS_TOKEN=your_facebook_page_access_token_here

# Discord
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
```

### File Structure

```
public/
├── templates/
│   └── news_temp.jpg          # Template image for framing
├── generated_images/          # Generated images storage
└── config/                    # Configuration files
```

## CLI Usage

Run the content generator from the command line:

```bash
# From the project root
python src/scripts/content_generator.py
```

The CLI provides an interactive interface for:
- Generating content from prompts
- Fetching latest blockchain news
- Generating images
- Posting to social media platforms

## Usage Examples

### Python Code Example

```python
from app.core.services.text_generation import TextGenerationService
from app.core.services.image_generation import ImageGenerationService
from app.core.services.social_media import SocialMediaService

# Initialize services
text_service = TextGenerationService()
image_service = ImageGenerationService()
social_service = SocialMediaService()

# Generate content
prompt = "The future of blockchain technology"
generated_text = await text_service.generate_text(prompt)
image_path = await image_service.generate_image(prompt, "my_image.png")

# Post to social media
result = await social_service.post_to_social_media(generated_text, image_path)
print(f"Posted successfully to: {result['successful_platforms']}")
```

### API Usage Example

```python
import requests

# Generate content
response = requests.post("http://localhost:8000/api/v1/content/generate", json={
    "prompt": "Blockchain innovation trends",
    "include_news": True
})

content = response.json()

# Post to social media
post_response = requests.post("http://localhost:8000/api/v1/content/post-to-social-media", json={
    "text": content["text"],
    "image_path": content["image_path"],
    "platforms": ["twitter", "linkedin"]
})
```

## Error Handling

The services include comprehensive error handling:
- **API Rate Limits**: Automatic retry with exponential backoff
- **Network Issues**: Graceful degradation and error reporting
- **Invalid Credentials**: Clear error messages for configuration issues
- **Platform Failures**: Individual platform failure tracking

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Environment Variables**: Use `.env` files for local development
3. **Authentication**: All API endpoints require user authentication
4. **Rate Limiting**: Respect platform rate limits and API quotas

## Troubleshooting

### Common Issues

1. **Missing API Keys**: Ensure all required environment variables are set
2. **Image Generation Failures**: Check OpenAI API quota and billing
3. **Social Media Posting Failures**: Verify platform credentials and permissions
4. **Template Image Missing**: Ensure `news_temp.jpg` exists in `public/templates/`

### Debug Mode

Enable debug logging by setting the environment to development:

```env
ENVIRONMENT=local
```

## Dependencies

The content generation features require these additional dependencies:
- `openai>=1.0.0`
- `requests>=2.31.0`
- `tweepy>=4.14.0`
- `instabot>=0.117.0`
- `pillow>=10.0.0`
- `requests-toolbelt>=1.0.0`

These are automatically included in the project's `pyproject.toml`. 