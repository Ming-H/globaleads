"""
系统设置接口 - AI 配置 + API 用量
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()


class AIConfigResponse(BaseModel):
    """AI 配置响应"""
    provider: str
    model: str
    base_url: str
    has_api_key: bool


class AIConfigUpdate(BaseModel):
    """更新 AI 配置"""
    provider: str = Field(..., pattern="^(ollama|deepseek)$")
    api_key: str | None = None


class APIUsageResponse(BaseModel):
    """API 用量响应"""
    reddit: dict
    bluesky: dict
    youtube: dict
    apollo: dict
    google_maps: dict
    hunter: dict


@router.get("/ai-config", response_model=AIConfigResponse)
async def get_ai_config(
    current_user: User = Depends(get_current_user),
):
    """
    查看当前 AI 配置（Ollama/DeepSeek）
    """
    return AIConfigResponse(
        provider=settings.AI_PROVIDER,
        model=settings.ai_model,
        base_url=settings.ai_base_url,
        has_api_key=bool(settings.ai_api_key),
    )


@router.patch("/ai-config")
async def update_ai_config(
    request: AIConfigUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    切换 AI 配置（运行时生效，需重启服务持久化）
    注意：此处修改的是运行时内存配置，持久化需更新 .env 文件
    """
    from app.core.config import get_settings

    if request.provider == "deepseek":
        if request.api_key:
            settings.DEEPSEEK_API_KEY = request.api_key
    elif request.provider == "ollama":
        pass  # Ollama 无需 API Key

    settings.AI_PROVIDER = request.provider

    return {
        "message": "AI 配置已更新",
        "provider": settings.AI_PROVIDER,
        "model": settings.ai_model,
        "base_url": settings.ai_base_url,
    }


@router.get("/api-usage", response_model=APIUsageResponse)
async def get_api_usage(
    current_user: User = Depends(get_current_user),
):
    """
    查看各 API 当前用量和剩余额度
    """
    usage = {}
    api_configs = {
        "reddit": {"limit": "60 requests/min", "monthly": None},
        "bluesky": {"limit": "3000 requests/5min", "monthly": None},
        "youtube": {"limit": "10000 units/day", "monthly": None},
        "apollo": {"limit": "900 credits/month", "monthly": 900},
        "google_maps": {"limit": "6250 requests/month", "monthly": 6250},
        "hunter": {"limit": "25 credits/month", "monthly": 25},
    }

    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        for api_name, config in api_configs.items():
            used = int(r.get(f"api_usage:{api_name}") or 0)
            remaining = (config["monthly"] - used) if config["monthly"] else None
            usage[api_name] = {
                "used": used,
                "limit": config["limit"],
                "remaining": remaining,
            }
        r.close()
    except Exception:
        for api_name, config in api_configs.items():
            usage[api_name] = {
                "used": 0,
                "limit": config["limit"],
                "remaining": config.get("monthly"),
            }

    return APIUsageResponse(**usage)
