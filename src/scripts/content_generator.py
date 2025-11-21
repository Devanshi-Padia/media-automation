#!/usr/bin/env python3
"""
Content Generator CLI Script
This script provides a command-line interface for generating and posting content to social media.
"""

import sys
import asyncio
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.services.text_generation import TextGenerationService
from app.core.services.image_generation import ImageGenerationService
from app.core.services.social_media import SocialMediaService

async def run_chat():
    """Main CLI interface for content generation."""
    print("\n🤖 AI Content Creator (Type 'exit' to quit)")
    print("=" * 50)

    # Initialize services
    try:
        text_service = TextGenerationService()
        image_service = ImageGenerationService()
        social_service = SocialMediaService()
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        print("Please check your .env file configuration.")
        return

    while True:
        user_prompt = input("\nEnter a topic to generate content (or 'news' for latest blockchain news): ").strip()

        if user_prompt.lower() == 'exit':
            break

        if user_prompt.lower() == 'news':
            print("\n📰 Fetching the latest blockchain news...")
            try:
                news_summary = text_service.fetch_blockchain_news()
                prompt = f"Based on the latest blockchain news:\n{news_summary}\n\nGenerate a post about the latest blockchain developments. Include 15 relevant hashtags."
            except Exception as e:
                print(f"❌ Error fetching news: {e}")
                continue
        else:
            prompt = user_prompt

        try:
            print("\n🔄 Generating content...")
            
            # 1. Generate text for all platforms
            generated_text = await text_service.generate_text(prompt)
            if not generated_text:
                print("❌ Error: No text generated.")
                continue

            print("\n📝 Generated text content:")
            for platform, text in generated_text.items():
                print(f"\n{platform.upper()}:")
                print(f"{text[:100]}..." if len(text) > 100 else text)

            # 2. Generate image based on prompt
            print("\n🎨 Generating image...")
            image_filename = f"generated_{int(asyncio.get_event_loop().time())}.png"
            image_path = await image_service.generate_image(prompt, image_filename)
            
            if not image_path:
                print("❌ Error: No image generated.")
                continue

            print(f"✅ Image generated: {image_path}")

            # 3. Ask user if they want to post to social media
            post_choice = input("\n🤔 Do you want to post this content to social media? (y/n): ").strip().lower()
            
            if post_choice in ['y', 'yes']:
                print("\n🚀 Posting to social media platforms...")
                result = await social_service.post_to_social_media(generated_text, image_path)
                
                if result['status'] == 'success':
                    print("✅ Successfully posted to all platforms!")
                elif result['status'] == 'partial':
                    print(f"⚠️ Partially successful:")
                    print(f"   ✅ Successful: {', '.join(result['successful_platforms'])}")
                    print(f"   ❌ Failed: {', '.join(result['failed_platforms'])}")
                else:
                    print(f"❌ Failed to post: {result.get('error', 'Unknown error')}")
            else:
                print("📁 Content saved locally. You can post it manually later.")

        except Exception as e:
            print(f"❌ Error: {e}")
            continue

    print("\n👋 Goodbye!")

def main():
    """Main entry point."""
    try:
        asyncio.run(run_chat())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
