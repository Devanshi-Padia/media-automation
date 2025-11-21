import uuid as uuid_pkg
from datetime import UTC, datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, String, JSON, Column, Integer, Boolean, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base

if TYPE_CHECKING:
    from .post import Post
    from .project import Project
    from .user import User


class PostAnalytics(Base):
    __tablename__ = "post_analytics"
    
    id: Mapped[int] = mapped_column("id", autoincrement=True, nullable=False, unique=True, primary_key=True, init=False)
    post_id: Mapped[int | None] = mapped_column(ForeignKey("post.id"), nullable=True, index=True)  # Made optional for project-level analytics
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # facebook, twitter, instagram, etc.
    post_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Engagement metrics
    likes: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    
    # Calculated metrics
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    click_through_rate: Mapped[float] = mapped_column(Float, default=0.0)
    
    # A/B Testing
    ab_test_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    variant: Mapped[str | None] = mapped_column(String(50), nullable=True)  # A, B, C, etc.
    
    # Data quality indicators
    data_quality_score: Mapped[float] = mapped_column(Float, default=1.0)  # 0.0 to 1.0
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    last_verified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    last_synced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships - made optional to handle project-level analytics
    post: Mapped["Post | None"] = relationship("Post", back_populates="analytics", init=False)
    project: Mapped["Project"] = relationship("Project", back_populates="post_analytics", init=False)


class AnalyticsTrend(Base):
    """Track analytics trends over time"""
    __tablename__ = "analytics_trends"
    
    id: Mapped[int] = mapped_column("id", autoincrement=True, nullable=False, unique=True, primary_key=True, init=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Trend data
    trend_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Aggregated metrics
    total_posts: Mapped[int] = mapped_column(Integer, default=0)
    total_engagement: Mapped[int] = mapped_column(Integer, default=0)
    total_reach: Mapped[int] = mapped_column(Integer, default=0)
    total_impressions: Mapped[int] = mapped_column(Integer, default=0)
    avg_engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_click_rate: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Growth metrics
    engagement_growth: Mapped[float] = mapped_column(Float, default=0.0)  # Percentage change
    reach_growth: Mapped[float] = mapped_column(Float, default=0.0)
    follower_growth: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="analytics_trends")


class AnalyticsInsight(Base):
    """Store actionable insights from analytics data"""
    __tablename__ = "analytics_insights"
    
    id: Mapped[int] = mapped_column("id", autoincrement=True, nullable=False, unique=True, primary_key=True, init=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False)  # performance, trend, anomaly, recommendation
    
    # Insight data
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="info")  # info, warning, critical
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 1.0
    
    # Insight details
    data_points: Mapped[dict] = mapped_column(JSON, nullable=True)  # Supporting data
    recommendations: Mapped[dict] = mapped_column(JSON, nullable=True)  # Actionable recommendations
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_actioned: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    actioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="analytics_insights")


class ABTest(Base):
    __tablename__ = "ab_tests"
    
    id: Mapped[int] = mapped_column("id", autoincrement=True, nullable=False, unique=True, primary_key=True, init=False)
    test_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Test configuration
    test_type: Mapped[str] = mapped_column(String(50), nullable=False)  # content, image, timing, etc.
    variants: Mapped[dict] = mapped_column(JSON, nullable=False)  # Store variant configurations
    traffic_split: Mapped[dict] = mapped_column(JSON, nullable=False)  # e.g., {"A": 50, "B": 50}
    
    # Test status
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, active, paused, completed
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Results
    winner: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="ab_tests")


class AnalyticsReport(Base):
    __tablename__ = "analytics_reports"
    
    id: Mapped[int] = mapped_column("id", autoincrement=True, nullable=False, unique=True, primary_key=True, init=False)
    report_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Report configuration
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # performance, engagement, ab_test, etc.
    report_name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_range: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"start": "2024-01-01", "end": "2024-01-31"}
    filters: Mapped[dict] = mapped_column(JSON, nullable=True)  # Platform filters, etc.
    
    # Report data
    data: Mapped[dict] = mapped_column(JSON, nullable=False)  # Actual report data
    summary: Mapped[dict] = mapped_column(JSON, nullable=True)  # Key metrics summary
    
    # Export options
    format: Mapped[str] = mapped_column(String(20), default="json")  # json, csv, pdf, excel
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="generating")  # generating, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="analytics_reports")
    user: Mapped["User"] = relationship("User", back_populates="analytics_reports") 