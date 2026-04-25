"""
数据库配置模块 - SQLAlchemy Async Engine + Session
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# 创建异步 Session 工厂
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """
    数据库会话依赖注入
    用于 FastAPI Depends
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """
    初始化数据库表
    在应用启动时调用
    """
    from app.models.base import Base
    async with engine.begin() as conn:
        # 导入所有模型以确保注册
        from app.models import user, social_task, social_lead, b2b_task, b2b_lead  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
