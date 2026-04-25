"""
B2B 线索相关请求/响应模型
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class B2BLeadResponse(BaseModel):
    """B2B 线索响应"""
    id: int
    task_id: int
    company_name: str
    company_website: Optional[str] = None
    company_size: Optional[str] = None
    company_address: Optional[str] = None
    region: Optional[str] = None
    industry: Optional[str] = None
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    email_verified: bool = False
    data_source: str
    source_url: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class B2BLeadListResponse(BaseModel):
    """B2B 线索列表响应"""
    total: int
    items: list[B2BLeadResponse]


class B2BLeadStatusUpdate(BaseModel):
    """更新 B2B 线索联系状态"""
    status: str = Field(..., pattern="^(uncontacted|contacted|replied|invalid)$")


class ExportRequest(BaseModel):
    """导出请求"""
    task_id: Optional[int] = None
    format: str = Field(default="csv", pattern="^(csv|xlsx)$")
    filters: dict = Field(default={}, description="筛选条件")
