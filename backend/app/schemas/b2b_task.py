"""
B2B 任务相关请求/响应模型
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class B2BTaskCreate(BaseModel):
    """创建 B2B 任务请求"""
    name: str = Field(..., min_length=1, max_length=200, description="任务名称")
    industry: Optional[str] = Field(None, max_length=200, description="目标行业")
    region: Optional[str] = Field(None, max_length=200, description="目标地区")
    company_size: Optional[str] = Field(None, max_length=50, description="公司规模范围")
    data_sources: list[str] = Field(..., min_length=1, description="数据源列表")
    max_results: int = Field(default=100, ge=1, le=1000, description="最大搜索数量")


class B2BTaskResponse(BaseModel):
    """B2B 任务响应"""
    id: int
    name: str
    industry: Optional[str] = None
    region: Optional[str] = None
    company_size: Optional[str] = None
    data_sources: list[str]
    status: str
    max_results: int
    lead_count: int
    error_message: Optional[str] = None
    celery_task_id: Optional[str] = None
    config: dict = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class B2BTaskListResponse(BaseModel):
    """B2B 任务列表响应"""
    total: int
    items: list[B2BTaskResponse]
