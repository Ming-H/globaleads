"""
社媒任务相关请求/响应模型
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SocialTaskCreate(BaseModel):
    """创建社媒任务请求"""
    name: str = Field(..., min_length=1, max_length=200, description="任务名称")
    keywords: list[str] = Field(..., min_length=1, description="关键词列表")
    platforms: list[str] = Field(..., min_length=1, description="目标平台列表")
    max_results: int = Field(default=100, ge=1, le=1000, description="最大采集数量")
    min_score: int = Field(default=50, ge=0, le=100, description="最低意向评分")


class SocialTaskResponse(BaseModel):
    """社媒任务响应"""
    id: int
    name: str
    keywords: list[str]
    platforms: list[str]
    status: str
    max_results: int
    min_score: int
    lead_count: int
    error_message: Optional[str] = None
    celery_task_id: Optional[str] = None
    config: dict = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SocialTaskListResponse(BaseModel):
    """社媒任务列表响应"""
    total: int
    items: list[SocialTaskResponse]
