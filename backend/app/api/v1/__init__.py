"""
API v1 路由模块
"""
from fastapi import APIRouter

from app.api.v1 import auth, social_tasks, social_leads, b2b_tasks, b2b_leads, dashboard, settings_router

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(social_tasks.router, prefix="/social-tasks", tags=["社媒任务"])
api_router.include_router(social_leads.router, prefix="/social-leads", tags=["社媒线索"])
api_router.include_router(b2b_tasks.router, prefix="/b2b-tasks", tags=["B2B任务"])
api_router.include_router(b2b_leads.router, prefix="/b2b-leads", tags=["B2B线索"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["数据看板"])
api_router.include_router(settings_router.router, prefix="/settings", tags=["系统设置"])
