from __future__ import annotations
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, ForeignKey, Text, DateTime, JSON, Float, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from ..core.db.database import Base
from datetime import datetime
from .project import Project

class MediaLibrary(Base):
    """Central media library for storing and organizing media files"""
    __tablename__ = "media_libraries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    media_files: Mapped[List["MediaFile"]] = relationship("MediaFile", back_populates="library", cascade="all, delete-orphan")
    collections: Mapped[List["MediaCollection"]] = relationship("MediaCollection", back_populates="library", cascade="all, delete-orphan")

class MediaFile(Base):
    """Individual media file (image or video)"""
    __tablename__ = "media_files"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True, init=False)
    library_id: Mapped[int] = mapped_column(Integer, ForeignKey("media_libraries.id"), nullable=False)
    
    # File information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # image/video
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Database storage fields
    file_data: Mapped[str] = mapped_column(Text, nullable=False)  # Base64 encoded file data
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # in bytes
    
    # Media properties
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # for videos, in seconds
    
    # Thumbnail (also stored in DB)
    thumbnail_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Base64 encoded thumbnail
    thumbnail_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Metadata
    file_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # EXIF, etc.
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Store tags as JSON
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    library: Mapped["MediaLibrary"] = relationship("MediaLibrary", back_populates="media_files")
    collections: Mapped[List["MediaCollectionItem"]] = relationship("MediaCollectionItem", back_populates="media_file", cascade="all, delete-orphan")
    projects: Mapped[List["ProjectMedia"]] = relationship("ProjectMedia", back_populates="media_file", cascade="all, delete-orphan")
    edits: Mapped[List["MediaEdit"]] = relationship("MediaEdit", back_populates="media_file", cascade="all, delete-orphan")

class MediaCollection(Base):
    """Collections to organize media files"""
    __tablename__ = "media_collections"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True, init=False)
    library_id: Mapped[int] = mapped_column(Integer, ForeignKey("media_libraries.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    library: Mapped["MediaLibrary"] = relationship("MediaLibrary", back_populates="collections")
    items: Mapped[List["MediaCollectionItem"]] = relationship("MediaCollectionItem", back_populates="collection", cascade="all, delete-orphan")

class MediaCollectionItem(Base):
    """Junction table for media files in collections"""
    __tablename__ = "media_collection_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True, init=False)
    collection_id: Mapped[int] = mapped_column(Integer, ForeignKey("media_collections.id"), nullable=False)
    media_file_id: Mapped[int] = mapped_column(Integer, ForeignKey("media_files.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    collection: Mapped["MediaCollection"] = relationship("MediaCollection", back_populates="items")
    media_file: Mapped["MediaFile"] = relationship("MediaFile", back_populates="collections")

class ProjectMedia(Base):
    """Junction table for media files used in projects"""
    __tablename__ = "project_media"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True, init=False)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    media_file_id: Mapped[int] = mapped_column(Integer, ForeignKey("media_files.id"), nullable=False)
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # specific platform or null for all
    usage_type: Mapped[str] = mapped_column(String(50), default="primary")  # primary, thumbnail, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    media_file: Mapped["MediaFile"] = relationship("MediaFile", back_populates="projects")
    project: Mapped["Project"] = relationship("Project")

class MediaEdit(Base):
    """Store media editing operations and their results"""
    __tablename__ = "media_edits"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True, init=False)
    media_file_id: Mapped[int] = mapped_column(Integer, ForeignKey("media_files.id"), nullable=False)
    
    # Edit information
    edit_type: Mapped[str] = mapped_column(String(50), nullable=False)  # crop, resize, filter, etc.
    edit_params: Mapped[dict] = mapped_column(JSON, nullable=False)  # Store edit parameters
    original_file_data: Mapped[str] = mapped_column(Text, nullable=False)
    edited_file_data: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    media_file: Mapped["MediaFile"] = relationship("MediaFile", back_populates="edits") 