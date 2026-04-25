"""
ORM 基类模块
"""
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 声明基类"""
    pass


class TimestampMixin:
    """时间戳混入类 - 为模型添加 created_at 和 updated_at"""
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class IntIDMixin:
    """整数 ID 混入类"""
    id = Column(Integer, primary_key=True, autoincrement=True)
