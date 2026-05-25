"""
B2B 线索模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.sql import func

from app.models.base import Base, IntIDMixin


class B2BLead(Base, IntIDMixin):
    """
    B2B 线索表

    Fields:
        id: 主键
        task_id: 关联任务（FK -> b2b_tasks.id）
        company_name: 公司名称
        company_website: 公司网站
        company_size: 公司规模
        company_address: 公司地址
        region: 所在地区
        industry: 行业分类
        contact_name: 联系人姓名
        contact_title: 联系人职位
        contact_email: 联系人邮箱
        contact_phone: 联系人电话
        contact_twitter: Twitter/X 账号
        contact_linkedin: LinkedIn 链接
        contact_facebook: Facebook 页面
        data_source: 数据来源 (google_search/osm)
        source_url: 来源页面 URL
        status: 联系状态 (uncontacted/contacted/replied/invalid)
        created_at: 创建时间
    """
    __tablename__ = "b2b_leads"

    task_id = Column(Integer, ForeignKey("b2b_tasks.id"), nullable=False, index=True)
    company_name = Column(String(300), nullable=False)
    company_website = Column(String(500), nullable=True)
    company_size = Column(String(50), nullable=True)
    company_address = Column(String(500), nullable=True)
    region = Column(String(200), nullable=True, index=True)
    industry = Column(String(200), nullable=True, index=True)
    contact_name = Column(String(200), nullable=True)
    contact_title = Column(String(200), nullable=True)
    contact_email = Column(String(255), nullable=True, index=True)
    contact_phone = Column(String(50), nullable=True)
    contact_twitter = Column(String(200), nullable=True)
    contact_linkedin = Column(String(500), nullable=True)
    contact_facebook = Column(String(500), nullable=True)
    data_source = Column(String(50), nullable=False, index=True)
    source_url = Column(String(500), nullable=True)
    status = Column(String(20), default="uncontacted", nullable=False, index=True)
    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<B2BLead(id={self.id}, company={self.company_name})>"
