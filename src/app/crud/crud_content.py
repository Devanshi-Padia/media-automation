from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from ..models.content import ContentGeneration, SocialMediaPost, UserPreferences
from ..schemas.content import ContentGenerationCreate, SocialMediaPostCreate, UserPreferencesCreate, UserPreferencesUpdate

class CRUDContentGeneration:
    def create(self, db: Session, *, obj_in: ContentGenerationCreate, user_id: int) -> ContentGeneration:
        """Create a new content generation record."""
        db_obj = ContentGeneration(
            user_id=user_id,
            prompt=obj_in.prompt,
            generated_text=obj_in.generated_text,
            image_path=obj_in.image_path,
            include_news=obj_in.include_news,
            platforms=obj_in.platforms
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: int) -> Optional[ContentGeneration]:
        """Get content generation by ID."""
        return db.query(ContentGeneration).filter(ContentGeneration.id == id).first()

    def get_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[ContentGeneration]:
        """Get content generations for a specific user."""
        return db.query(ContentGeneration).filter(ContentGeneration.user_id == user_id).offset(skip).limit(limit).all()

    def update(self, db: Session, *, db_obj: ContentGeneration, obj_in: Dict[str, Any]) -> ContentGeneration:
        """Update content generation."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db_obj.updated_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: int) -> ContentGeneration:
        """Delete content generation."""
        obj = db.query(ContentGeneration).get(id)
        db.delete(obj)
        db.commit()
        return obj

class CRUDSocialMediaPost:
    def create(self, db: Session, *, obj_in: SocialMediaPostCreate) -> SocialMediaPost:
        """Create a new social media post record."""
        db_obj = SocialMediaPost(
            content_generation_id=obj_in.content_generation_id,
            platform=obj_in.platform,
            post_text=obj_in.post_text,
            image_path=obj_in.image_path,
            status=obj_in.status
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: int) -> Optional[SocialMediaPost]:
        """Get social media post by ID."""
        return db.query(SocialMediaPost).filter(SocialMediaPost.id == id).first()

    def get_by_content_generation(self, db: Session, content_generation_id: int) -> List[SocialMediaPost]:
        """Get all posts for a content generation."""
        return db.query(SocialMediaPost).filter(SocialMediaPost.content_generation_id == content_generation_id).all()

    def update_status(self, db: Session, *, id: int, status: str, error_message: Optional[str] = None, platform_response: Optional[Dict] = None) -> SocialMediaPost:
        """Update post status."""
        db_obj = db.query(SocialMediaPost).get(id)
        if db_obj:
            db_obj.status = status
            if status == "success":
                db_obj.posted_at = datetime.utcnow()
            if error_message:
                db_obj.error_message = error_message
            if platform_response:
                db_obj.platform_response = platform_response
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def get_by_platform(self, db: Session, platform: str, user_id: int, skip: int = 0, limit: int = 100) -> List[SocialMediaPost]:
        """Get posts by platform for a user."""
        return db.query(SocialMediaPost).join(ContentGeneration).filter(
            and_(
                SocialMediaPost.platform == platform,
                ContentGeneration.user_id == user_id
            )
        ).offset(skip).limit(limit).all()

class CRUDUserPreferences:
    def create(self, db: Session, *, obj_in: UserPreferencesCreate) -> UserPreferences:
        """Create user preferences."""
        db_obj = UserPreferences(
            user_id=obj_in.user_id,
            default_platforms=obj_in.default_platforms,
            include_news_by_default=obj_in.include_news_by_default,
            auto_post=obj_in.auto_post,
            content_style=obj_in.content_style,
            hashtag_count=obj_in.hashtag_count
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, user_id: int) -> Optional[UserPreferences]:
        """Get user preferences."""
        return db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()

    def update(self, db: Session, *, db_obj: UserPreferences, obj_in: UserPreferencesUpdate) -> UserPreferences:
        """Update user preferences."""
        for field, value in obj_in.dict(exclude_unset=True).items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db_obj.updated_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_or_create(self, db: Session, *, user_id: int) -> UserPreferences:
        """Get user preferences or create default ones."""
        preferences = self.get(db, user_id)
        if not preferences:
            preferences = self.create(db, obj_in=UserPreferencesCreate(
                user_id=user_id,
                default_platforms=["twitter", "linkedin"],
                include_news_by_default=True,
                auto_post=False,
                content_style="professional",
                hashtag_count=15
            ))
        return preferences

# Create instances
content_generation = CRUDContentGeneration()
social_media_post = CRUDSocialMediaPost()
user_preferences = CRUDUserPreferences() 