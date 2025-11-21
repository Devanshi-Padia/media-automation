from sqlalchemy import Column, Integer, String, JSON
from ..core.db.database import Base

class ContentReview(Base):
    __tablename__ = "content_review"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(JSON, nullable=False)
    image_path = Column(String, nullable=True)
