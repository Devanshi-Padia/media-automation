import openai
import requests
import os
import time
import re
from typing import Dict, Optional
from ...core.config import settings

class TextGenerationService:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.news_api_key = settings.NEWS_API_KEY
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is missing!")
        openai.api_key = self.openai_api_key

    def clean_text(self, text: str) -> str:
        """Clean up the generated text by removing unwanted patterns."""
        return re.sub(r"(\[\/INST\]|\[INST\]|\|<\/s>|\<\|start_of_turn\|\>|\<\|end_of_turn\|\>|\*\*\s*|\*\s*|\*\*+$|\[.*?\])", "", text).strip()

    def trim_to_last_sentence(self, text: str, limit: int = 280) -> str:
        """Trim text to the last sentence that fits within the character limit."""
        if len(text) <= limit:
            return text
        sentences = re.split(r'(?<=[.!?])\s+', text)
        trimmed_text = ''
        for sentence in sentences:
            if len(trimmed_text + sentence) <= limit:
                trimmed_text += sentence
            else:
                break
        return trimmed_text.strip()

    def delay(self, ms: int):
        """Delay function to add pauses between retries."""
        time.sleep(ms / 1000.0)

    def fetch_news(self, topic: str) -> str:
        """Fetch news for a given topic from the News API."""
        try:
            if not self.news_api_key:
                return f"No news API key configured. Cannot fetch news for {topic}."
            url = f'https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&apiKey={self.news_api_key}'
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if 'articles' not in data or not data['articles']:
                return f"No recent news articles found for '{topic}'. Please generate content based on general knowledge about this topic."
            
            news_summary = "\n\n".join([
                f"Title: {article['title']}\nDescription: {article.get('description', 'No description available.')}"
                for article in data['articles'][:3]
            ])
            return news_summary
        except Exception as e:
            return f"Error fetching news for '{topic}': {e}. Please generate content based on general knowledge about this topic."

    def generate_text(self, topic: str, content_type: str) -> Dict[str, str]:
        """Generate text content, using news API if content_type is 'news'."""
        try:
            prompt_for_openai = ""
            if content_type.lower() == 'news':
                news_context = self.fetch_news(topic)
                prompt_for_openai = f"Based on the following news articles about '{topic}', write an engaging social media post. Do not just list the news, but create a cohesive and interesting summary or take on them. Include relevant hashtags.\n\nNews context:\n{news_context}"
            else:
                prompt_for_openai = f"Create a '{content_type}' text for a social media project about the following topic: {topic}. Conclude with relevant hashtags."

            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": "You are a social media content creator. Generate a post suitable for all platforms. Be engaging and informative. Conclude with relevant hashtags."
                }, {
                    "role": "user",
                    "content": prompt_for_openai
                }]
            )
            base_text = response.choices[0].message.content or ""
            base_text = self.clean_text(base_text)
            trimmed = self.trim_to_last_sentence(base_text, 280) if base_text else "No content generated."
            other_platforms = self.trim_to_last_sentence(base_text, 1000) if base_text else "No content generated."
            
            # Generate platform-specific content
            telegram_content = f"📢 {base_text}\n\nStay updated with the latest insights on {topic}. Join our channel for more updates! 📱"
            
            results = {
                "twitter": trimmed,
                "x": trimmed,
                "facebook": other_platforms,
                "instagram": other_platforms,
                "linkedin": other_platforms,
                "discord": other_platforms,
                "telegram": telegram_content
            }
            return results
        except Exception as e:
            print(f"Error generating text: {e}")
            return {p: str(e) for p in ["twitter", "x", "facebook", "instagram", "linkedin", "discord", "telegram"]}