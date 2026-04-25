"""
数据看板相关请求/响应模型
"""
from typing import Optional

from pydantic import BaseModel, Field


class SocialLeadsStats(BaseModel):
    """社媒线索统计"""
    total: int = 0
    this_week: int = 0
    by_platform: dict[str, int] = {}
    avg_score: float = 0.0
    by_tag: dict[str, int] = {}


class B2BLeadsStats(BaseModel):
    """B2B 线索统计"""
    total: int = 0
    this_week: int = 0
    by_source: dict[str, int] = {}
    with_email: int = 0
    by_industry: dict[str, int] = {}


class TasksStats(BaseModel):
    """任务统计"""
    social_total: int = 0
    b2b_total: int = 0
    success_rate: float = 0.0


class APIUsage(BaseModel):
    """API 用量"""
    used: int = 0
    limit: str = ""


class StatsResponse(BaseModel):
    """看板统计数据响应"""
    social_leads: SocialLeadsStats = {}
    b2b_leads: B2BLeadsStats = {}
    tasks: TasksStats = {}
    api_usage: dict[str, APIUsage] = {}


class TrendItem(BaseModel):
    """趋势数据项"""
    date: str
    social_leads: int = 0
    b2b_leads: int = 0


class TrendsResponse(BaseModel):
    """趋势数据响应"""
    period: str
    items: list[TrendItem] = []
