"""
社媒线索相关请求/响应模型
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SocialLeadResponse(BaseModel):
    """社媒线索响应"""
    id: int
    task_id: int
    platform: str
    author_name: str
    author_url: Optional[str] = None
    content: str
    post_url: Optional[str] = None
    published_at: Optional[datetime] = None
    ai_score: int
    ai_tags: list[str] = []
    ai_analysis: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SocialLeadListResponse(BaseModel):
    """社媒线索列表响应"""
    total: int
    items: list[SocialLeadResponse]


class SocialLeadStatusUpdate(BaseModel):
    """更新社媒线索联系状态"""
    status: str = Field(..., pattern="^(uncontacted|contacted|replied|invalid)$")


class ExportRequest(BaseModel):
    """导出请求"""
    task_id: Optional[int] = None
    format: str = Field(default="csv", pattern="^(csv|xlsx)$")
    filters: dict = Field(default={}, description="筛选条件")
