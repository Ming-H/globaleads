"""
社媒线索模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base, IntIDMixin


class SocialLead(Base, IntIDMixin):
    """
    社媒线索表

    Fields:
        id: 主键
        task_id: 关联任务（FK -> social_tasks.id）
        platform: 来源平台 (reddit/bluesky/youtube)
        author_name: 发帖人昵称
        author_url: 发帖人主页链接
        content: 帖子/评论内容
        post_url: 原帖链接
        published_at: 帖子发布时间
        ai_score: AI 意向评分 1-100
        ai_tags: AI 意向标签 JSONB
        ai_analysis: AI 分析详细结果
        status: 联系状态 (uncontacted/contacted/replied/invalid)
        created_at: 创建时间
    """
    __tablename__ = "social_leads"

    task_id = Column(Integer, ForeignKey("social_tasks.id"), nullable=False, index=True)
    platform = Column(String(20), nullable=False, index=True)
    author_name = Column(String(200), nullable=False)
    author_url = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    post_url = Column(String(500), nullable=True)
    published_at = Column(DateTime, nullable=True)
    ai_score = Column(Integer, default=0, index=True)
    ai_tags = Column(JSONB, default=[])
    ai_analysis = Column(Text, nullable=True)
    status = Column(String(20), default="uncontacted", nullable=False, index=True)
    created_at = Column(
        DateTime,
        server_default="now()",
        nullable=False,
    )

    __table_args__ = (
        Index("idx_social_leads_score", ai_score.desc()),
    )

    def __repr__(self):
        return f"<SocialLead(id={self.id}, platform={self.platform}, score={self.ai_score})>"
