"""
GlobalLeads FastAPI 主应用

海外线索挖掘平台 - 帮助中国外贸/跨境电商企业挖掘海外销售线索
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging_config import setup_logging
from app.middleware.logging import LoggingMiddleware
from app.api.v1 import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 初始化日志系统（最先执行）
    setup_logging()
    logger.info("GlobalLeads API 启动中...")

    # 初始化数据库
    await init_db()
    await create_default_data()

    logger.info("GlobalLeads API 启动完成 | port=%s", settings.PORT)

    yield

    logger.info("GlobalLeads API 关闭中...")
    await close_db()
    logger.info("GlobalLeads API 已关闭")


app = FastAPI(
    title="GlobalLeads API",
    description="海外线索挖掘平台 API - 帮助中国外贸/跨境电商企业挖掘海外销售线索",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
app.add_middleware(LoggingMiddleware)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "GlobalLeads API",
        "version": "1.0.0",
        "description": "海外线索挖掘平台",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/api/health")
async def health():
    """健康检查 - 检查 PostgreSQL 和 Redis 连通性"""
    checks = {}
    overall_ok = True

    try:
        from sqlalchemy import text
        from app.core.database import async_session
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        overall_ok = False

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        overall_ok = False

    return {
        "status": "ok" if overall_ok else "degraded",
        "version": "1.0.0",
        "checks": checks,
    }


async def create_default_data():
    """创建默认数据（默认管理员账号）"""
    from sqlalchemy import select
    from app.core.database import async_session
    from app.models.user import User
    from app.core.security import hash_password

    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.username == "admin")
        )
        admin = result.scalar_one_or_none()

        if not admin:
            admin = User(
                username="admin",
                email="admin@globaleads.com",
                hashed_password=hash_password(os.getenv("ADMIN_PASSWORD", "changeme")),
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            logger.info("默认管理员账号已创建 (admin)")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
    )
