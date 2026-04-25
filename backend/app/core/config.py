"""
核心配置模块 - 环境变量管理
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""

    # 应用信息
    APP_NAME: str = "GlobalLeads API"
    APP_VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://globaleads:globaleads_dev@localhost:5432/globaleads"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/1"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # AI 提供商切换
    AI_PROVIDER: str = "ollama"  # "ollama" 或 "deepseek"

    # Ollama 配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:0.6b"

    # DeepSeek 配置
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # JWT
    JWT_SECRET: str = "globaleads-change-this-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 72

    # Reddit API
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "GlobalLeads/1.0"

    # Bluesky API
    BLUESKY_HANDLE: str = ""
    BLUESKY_PASSWORD: str = ""

    # YouTube API
    YOUTUBE_API_KEY: str = ""

    # Apollo API
    APOLLO_API_KEY: str = ""

    # Google Maps API
    GOOGLE_MAPS_API_KEY: str = ""

    # Hunter.io API
    HUNTER_API_KEY: str = ""

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # 服务端口
    PORT: int = 8002

    # 分页
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @property
    def cors_origins_list(self) -> list[str]:
        """将 CORS_ORIGINS 逗号分隔字符串转为列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def ai_base_url(self) -> str:
        """获取当前 AI 提供商的 base URL"""
        if self.AI_PROVIDER == "deepseek":
            return self.DEEPSEEK_BASE_URL
        return self.OLLAMA_BASE_URL

    @property
    def ai_api_key(self) -> str:
        """获取当前 AI 提供商的 API Key"""
        if self.AI_PROVIDER == "deepseek":
            return self.DEEPSEEK_API_KEY
        return ""  # Ollama 无需 Key

    @property
    def ai_model(self) -> str:
        """获取当前 AI 提供商的模型名称"""
        if self.AI_PROVIDER == "deepseek":
            return self.DEEPSEEK_MODEL
        return self.OLLAMA_MODEL

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
