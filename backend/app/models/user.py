"""
用户模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin, IntIDMixin


class User(Base, IntIDMixin, TimestampMixin):
    """
    用户表

    Fields:
        id: 主键
        username: 用户名（唯一）
        email: 邮箱（唯一）
        hashed_password: 加密密码
        is_active: 是否启用
        created_at: 创建时间
        updated_at: 更新时间
    """
    __tablename__ = "users"

    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"
