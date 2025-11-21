from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from uuid import UUID


# Post Analytics Schemas
class PostAnalyticsBase(BaseModel):
    post_id: int
    project_id: int
    platform: str
    post_url: Optional[str] = None
    likes: int = 0
    shares: int = 0
    comments: int = 0
    reach: int = 0
    impressions: int = 0
    clicks: int = 0
    engagement_rate: float = 0.0
    click_through_rate: float = 0.0
    ab_test_id: Optional[str] = None
    variant: Optional[str] = None


class PostAnalyticsCreate(PostAnalyticsBase):
    pass


class PostAnalyticsUpdate(BaseModel):
    likes: Optional[int] = None
    shares: Optional[int] = None
    comments: Optional[int] = None
    reach: Optional[int] = None
    impressions: Optional[int] = None
    clicks: Optional[int] = None
    engagement_rate: Optional[float] = None
    click_through_rate: Optional[float] = None
    post_url: Optional[str] = None
    last_synced: Optional[datetime] = None


class PostAnalyticsResponse(PostAnalyticsBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_synced: Optional[datetime] = None

    class Config:
        from_attributes = True


class PostAnalyticsRead(PostAnalyticsBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_synced: Optional[datetime] = None

    class Config:
        from_attributes = True


# A/B Testing Schemas
class ABTestBase(BaseModel):
    project_id: int
    name: str
    description: Optional[str] = None
    test_type: str = Field(..., description="Type of test: content, image, timing, etc.")
    variants: Dict[str, Any] = Field(..., description="Variant configurations")
    traffic_split: Dict[str, int] = Field(..., description="Traffic split percentages")


class ABTestCreate(ABTestBase):
    pass


class ABTestUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    winner: Optional[str] = None
    confidence_level: Optional[float] = None


class ABTestResponse(ABTestBase):
    id: int
    test_id: str
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    winner: Optional[datetime] = None
    confidence_level: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ABTestRead(ABTestBase):
    id: int
    test_id: str
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    winner: Optional[str] = None
    confidence_level: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Analytics Report Schemas
class AnalyticsReportBase(BaseModel):
    project_id: int
    report_type: str = Field(..., description="Type of report: performance, engagement, ab_test, etc.")
    report_name: str
    date_range: Dict[str, str] = Field(..., description="Date range for the report")
    filters: Optional[Dict[str, Any]] = None
    format: str = "json"


class AnalyticsReportCreate(AnalyticsReportBase):
    pass


class AnalyticsReportUpdate(BaseModel):
    status: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class AnalyticsReportResponse(AnalyticsReportBase):
    id: int
    report_id: str
    user_id: int
    data: Dict[str, Any]
    summary: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AnalyticsReportRead(AnalyticsReportBase):
    id: int
    report_id: str
    user_id: int
    data: Dict[str, Any]
    summary: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Analytics Summary Schemas
class AnalyticsSummary(BaseModel):
    total_posts: int
    total_engagement: int
    total_likes: int = 0
    total_shares: int = 0
    total_comments: int = 0
    average_engagement_rate: float
    total_reach: int = 0
    total_impressions: int = 0
    total_clicks: int = 0
    average_click_rate: float = 0.0
    top_performing_platform: str
    top_performing_post_id: Optional[int] = None
    date_range: Dict[str, str]
    platform_breakdown: Dict[str, Dict[str, Any]]


class PostPerformanceMetrics(BaseModel):
    post_id: int
    title: str
    platform: str
    likes: int
    shares: int
    comments: int
    reach: int
    impressions: int
    clicks: int
    engagement_rate: float
    click_through_rate: float
    posted_at: Optional[datetime] = None


class ABTestResults(BaseModel):
    test_id: str
    test_name: str
    status: str
    variants: Dict[str, Dict[str, Any]]
    winner: Optional[str] = None
    confidence_level: Optional[float] = None
    total_participants: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# Request/Response schemas for API endpoints
class AnalyticsFilterRequest(BaseModel):
    project_id: int
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    platforms: Optional[List[str]] = None
    post_ids: Optional[List[int]] = None


class GenerateReportRequest(BaseModel):
    project_id: int
    report_type: str
    report_name: str
    date_range: Dict[str, str]
    filters: Optional[Dict[str, Any]] = None
    format: str = "json"


class SyncAnalyticsRequest(BaseModel):
    project_id: int
    post_ids: Optional[List[int]] = None
    platforms: Optional[List[str]] = None 