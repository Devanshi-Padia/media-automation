import openai
import shutil
import os
from PIL import Image, ImageDraw, ImageFont
import requests
import time
import base64
from io import BytesIO
from typing import Optional
from ...core.config import settings

class ImageGenerationService:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is missing!")
        openai.api_key = self.openai_api_key
        self.template_path = os.path.join("public", "templates", "news_temp.jpg")
        self.output_dir = os.path.join("public", "generated_images")
        os.makedirs(self.output_dir, exist_ok=True)

    def resize_image(self, input_path: str, output_path: str):
        """Resize image to 1200x1200 pixels."""
        try:
            image = Image.open(input_path)
            image = image.resize((1200, 1200), Image.Resampling.LANCZOS)
            image.save(output_path, format='JPEG', quality=85)
            return True
        except Exception as e:
            raise Exception(f"Error resizing image: {e}")

    def enhance_prompt(self, prompt: str) -> str:
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": f"Enhance this prompt for a photorealistic image: \"{prompt}\""}]
            )
            content = response.choices[0].message.content if response.choices and response.choices[0].message else None
            return content.strip() if content else prompt
        except Exception as e:
            return prompt

    # def generate_short_text(self, prompt: str) -> str:
    #     try:
    #         response = openai.chat.completions.create(
    #             model="gpt-4o-mini",
    #             messages=[{"role": "user", "content": f"Write a 40-word summary about: {prompt}"}]
    #         )
    #         content = response.choices[0].message.content if response.choices and response.choices[0].message else None
    #         return content.strip() if content else "Latest updates in the blockchain space. Stay tuned for more developments."
    #     except Exception as e:
    #         return "Latest updates in the blockchain space. Stay tuned for more developments."

    # def generate_headline(self, prompt: str) -> str:
    #     try:
    #         response = openai.chat.completions.create(
    #             model="gpt-4o-mini",
    #             messages=[{"role": "user", "content": f"Generate a short, impactful headline about: {prompt}. DO NOT include any words from prompt. Directly display the headline. DO NOT give incomplete sentence. End with a ! mark."}]
    #         )
    #         content = response.choices[0].message.content if response.choices and response.choices[0].message else None
    #         return content.strip() if content else "Breaking Blockchain News"
    #     except Exception as e:
    #         return "Breaking Blockchain News"

    # def wrap_text(self, draw, text: str, x: int, y: int, max_width: int, line_height: int, font):
    #     """Wrap text to fit within specified width."""
    #     words = text.split(" ")
    #     lines = []
    #     line = ""
    #     for word in words:
    #         test_line = line + word + " "
    #         bbox = draw.textbbox((0, 0), test_line, font=font)
    #         width = bbox[2] - bbox[0]
    #         if width > max_width:
    #             lines.append(line)
    #             line = word + " "
    #         else:
    #             line = test_line
    #     lines.append(line)

    #     for i, line in enumerate(lines):
    #         draw.text((x, y + i * line_height), line, font=font, fill="black")

    # def wrap_headline(self, draw, text: str, x: int, y: int, max_width: int, font):
    #     """Wrap headline text to fit within specified width."""
    #     words = text.split(" ")
    #     lines = []
    #     line = ""
    #     line_height = 100
    #     for word in words:
    #         test_line = line + word + " "
    #         bbox = draw.textbbox((0, 0), test_line, font=font)
    #         width = bbox[2] - bbox[0]
    #         if width > max_width:
    #             lines.append(line)
    #             line = word + " "
    #         else:
    #             line = test_line
    #     lines.append(line)

    #     total_height = len(lines) * line_height
    #     start_y = y - total_height / 2 + line_height / 2

    #     for i, line in enumerate(lines):
    #         draw.text((x, start_y + i * line_height), line, font=font, fill="white")

    # def create_framed_image(self, generated_image_path: str, output_path: str, headline: str, short_text: str) -> str:
    #     """Create framed image with text overlay."""
    #     try:
    #         if not os.path.exists(self.template_path):
    #             raise Exception("Template image not found")
                
    #         template_img = Image.open(self.template_path)
    #         generated_img = Image.open(generated_image_path)

    #         img_width, img_height = template_img.size
    #         canvas = Image.new('RGB', (img_width, img_height))
    #         canvas.paste(template_img, (0, 0))

    #         img_x, img_y = 450, 690
    #         img_width, img_height = img_width - 900, 920
    #         canvas.paste(generated_img, (img_x, img_y))

    #         draw = ImageDraw.Draw(canvas)
    #         font = ImageFont.truetype("arial.ttf", 80)

    #         # Use local wrap_headline and wrap_text functions instead of self.
    #         self.wrap_headline(draw, headline, int(img_width / 1.9), 430, img_width - 600, font)
    #         self.wrap_text(draw, short_text, int(img_width / 12), 1770, img_width - 300, 100, font)

    #         canvas.save(output_path)
    #         return output_path
    #     except Exception as e:
    #         raise Exception(f"Error creating framed image: {e}")

    # def create_platform_template(self, prompt: str, text: str, image_path: str, output_filename: str) -> str:
    #     """Create a standardized template with image and text layout."""
    #     try:
    #         # Create a new image with fixed dimensions (1200x1500)
    #         template = Image.new('RGB', (1200, 1500), 'white')
            
    #         # Load and resize the generated image for the top part
    #         content_image = Image.open(image_path)
    #         content_image.thumbnail((1200, 800))
            
    #         # Calculate positions
    #         image_y = 0  # Image at top
    #         text_y = 850  # Text below image with padding
            
    #         # Paste the image at the top
    #         template.paste(content_image, (0, image_y))
            
    #         # Add text in the bottom section
    #         draw = ImageDraw.Draw(template)
    #         try:
    #             font = ImageFont.truetype("arial.ttf", 40)
    #         except:
    #             font = ImageFont.load_default()
                
    #         # Word wrap text
    #         words = text.split()
    #         lines = []
    #         current_line = []
            
    #         for word in words:
    #             current_line.append(word)
    #             test_line = ' '.join(current_line)
    #             w = draw.textlength(test_line, font=font)
    #             if w > 1100:  # Leave some margin
    #                 if current_line:
    #                     current_line.pop()
    #                     lines.append(' '.join(current_line))
    #                     current_line = [word]
            
    #         if current_line:
    #             lines.append(' '.join(current_line))
            
    #         # Draw text lines
    #         line_height = 50
    #         for i, line in enumerate(lines):
    #             draw.text((50, text_y + i * line_height), line, fill='black', font=font)
            
    #         # Save the final template
    #         output_path = os.path.join(self.output_dir, output_filename)
    #         template.save(output_path, 'JPEG', quality=95)
    #         return output_path
            
    #     except Exception as e:
    #         print(f"Error creating platform template: {e}")
    #         return image_path  # Return original image as fallback

    async def generate_image(self, prompt: str, output_filename: str, max_retries: int = 3, base_delay: int = 2) -> str:
        for attempt in range(1, max_retries + 1):
            try:
                enhanced_prompt = self.enhance_prompt(prompt)
                response = openai.images.generate(
                    model="dall-e-3",
                    prompt=enhanced_prompt,
                    n=1,
                    size="1024x1024",
                    response_format="b64_json"
                )
                b64_data = None
                if hasattr(response, 'data') and response.data and hasattr(response.data[0], 'b64_json'):
                    b64_data = response.data[0].b64_json
                if not b64_data or not isinstance(b64_data, str):
                    raise Exception("No valid image data returned from OpenAI API.")
                img_data = base64.b64decode(b64_data)
                final_output_path = os.path.join(self.output_dir, output_filename)
                with open(final_output_path, 'wb') as img_file:
                    img_file.write(img_data)
                # --- Ensure PNG, RGB, and resize to 1024x1024 ---
                from PIL import Image
                try:
                    with Image.open(final_output_path) as img:
                        img = img.convert('RGB')
                        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                        img.save(final_output_path, format='PNG')
                        # Also save as JPEG for Twitter
                        jpeg_path = os.path.splitext(final_output_path)[0] + '.jpg'
                        img.save(jpeg_path, format='JPEG', quality=85)
                except Exception as e:
                    print(f"Error resizing/converting PNG/JPEG: {e}")
                # --- End ensure PNG/JPEG ---
                return final_output_path
            except Exception as e:
                if attempt == max_retries:
                    raise Exception(f"Failed after {max_retries} attempts: {e}")
                delay_time = base_delay * attempt
                time.sleep(delay_time)
        raise Exception("Failed to generate image after all retries")

    def compress_image_for_social_media(self, input_path: str, platform: str) -> str:
        """Compress image for social media platforms."""
        max_sizes = {
            "twitter": 5 * 1024 * 1024,
            "discord": 8 * 1024 * 1024
        }

        img = Image.open(input_path)
        img = img.convert("RGB")
        img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
        img.save(input_path, format="JPEG", quality=80)

        with open(input_path, 'rb') as f:
            img_size = len(f.read())

        if img_size > max_sizes.get(platform, float('inf')):
            img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
            img.save(input_path, format="JPEG", quality=70)

        return input_path