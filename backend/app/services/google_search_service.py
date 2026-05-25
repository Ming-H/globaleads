"""
Google Custom Search JSON API 搜索服务

免费额度：100 次查询/天。
用于搜索指定行业+地区的公司网站。
配额追踪使用 Redis，跨进程共享。
"""
import time
import asyncio
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DAILY_QUOTA = 100


def _redis_incr_daily_quota() -> int:
    """通过 Redis INCR 追踪每日配额，返回当日已用次数"""
    today = time.strftime("%Y-%m-%d")
    key = f"google_search_quota:{today}"
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        used = r.incr(key)
        if used == 1:
            r.expire(key, 86400 * 2)  # 2 天后自动过期
        r.close()
        return used
    except Exception:
        return 0


def _redis_get_daily_quota() -> int:
    """获取当日已用配额"""
    today = time.strftime("%Y-%m-%d")
    key = f"google_search_quota:{today}"
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        used = int(r.get(key) or 0)
        r.close()
        return used
    except Exception:
        return 0


def _check_daily_quota() -> bool:
    """检查是否还有配额，有则消耗 1 次"""
    used = _redis_incr_daily_quota()
    if used > DAILY_QUOTA:
        return False
    return True


class GoogleSearchService:
    """Google Custom Search API 封装"""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self):
        self.api_key = settings.GOOGLE_SEARCH_API_KEY
        self.cx = settings.GOOGLE_SEARCH_CX
        self._last_request_time: float = 0
        self._min_interval: float = 1.0
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _rate_limit(self):
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def search_companies(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict]:
        """
        搜索公司网站

        Args:
            query: 搜索查询词（如 "LED lighting distributors USA"）
            max_results: 最大结果数（每次 API 调用最多 10 条）

        Returns:
            公司列表
        """
        if not _check_daily_quota():
            raise RuntimeError("Google Custom Search 每日配额已用完（100 次/天）")

        await self._rate_limit()
        client = await self._get_client()

        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(max_results, 10),
        }

        resp = await client.get(self.BASE_URL, params=params)
        resp.raise_for_status()

        data = resp.json()
        results = []
        for item in data.get("items", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "display_link": item.get("displayLink", ""),
            })

        return results

    @property
    def daily_quota_used(self) -> int:
        return _redis_get_daily_quota()

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class GoogleSearchSyncService:
    """Google Custom Search 同步封装（供 Celery 任务使用）"""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self):
        self.api_key = settings.GOOGLE_SEARCH_API_KEY
        self.cx = settings.GOOGLE_SEARCH_CX
        self._last_request_time: float = 0
        self._min_interval: float = 1.0

    def _rate_limit(self):
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def search_companies(self, query: str, max_results: int = 10) -> list[dict]:
        """同步搜索公司网站"""
        if not _check_daily_quota():
            raise RuntimeError("Google Custom Search 每日配额已用完（100 次/天）")

        self._rate_limit()

        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(max_results, 10),
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(self.BASE_URL, params=params)
            resp.raise_for_status()

        data = resp.json()
        results = []
        for item in data.get("items", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "display_link": item.get("displayLink", ""),
            })

        return results
