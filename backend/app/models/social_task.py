"""
社媒挖掘任务模型
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base, TimestampMixin, IntIDMixin


class SocialTask(Base, IntIDMixin, TimestampMixin):
    """
    社媒挖掘任务表

    Fields:
        id: 主键
        user_id: 创建者（FK -> users.id）
        name: 任务名称
        keywords: 关键词列表 JSONB
        platforms: 目标平台 JSONB
        max_results: 最大采集数量
        min_score: 最低意向评分
        status: 任务状态 (pending/running/completed/failed/quota_exceeded)
        error_message: 失败时的错误信息
        lead_count: 发现的线索数量
        celery_task_id: Celery 任务 ID
        config: 额外配置 JSONB
        created_at: 创建时间
        updated_at: 更新时间
    """
    __tablename__ = "social_tasks"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    keywords = Column(JSONB, nullable=False)
    platforms = Column(JSONB, nullable=False)
    max_results = Column(Integer, default=100)
    min_score = Column(Integer, default=50)
    status = Column(String(20), default="pending", nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    lead_count = Column(Integer, default=0)
    celery_task_id = Column(String(255), nullable=True)
    config = Column(JSONB, default={})

    def __repr__(self):
        return f"<SocialTask(id={self.id}, name={self.name}, status={self.status})>"
