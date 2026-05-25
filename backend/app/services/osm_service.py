"""
OpenStreetMap Nominatim API 搜索服务

完全免费，1 请求/秒速率限制。
用于按地区+关键词搜索本地商家。
无需 API Key。
"""
import time
import asyncio
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OSMService:
    """OpenStreetMap Nominatim API 封装"""

    BASE_URL = "https://nominatim.openstreetmap.org"

    def __init__(self):
        self._last_request_time: float = 0
        self._min_interval: float = 1.1  # Nominatim 要求 <= 1 req/s
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "GlobalLeads/1.0"},
            )
        return self._client

    async def _rate_limit(self):
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def search_businesses(
        self,
        query: str,
        region: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """
        搜索本地商家

        Args:
            query: 搜索关键词（如 "LED lighting store"）
            region: 地区限定（如 "California, USA"）
            limit: 返回数量限制

        Returns:
            商家列表
        """
        await self._rate_limit()
        client = await self._get_client()

        search_query = query
        if region:
            search_query = f"{query}, {region}"

        params = {
            "q": search_query,
            "format": "json",
            "limit": min(limit, 50),
            "addressdetails": 1,
            "extratags": 1,
        }

        resp = await client.get(f"{self.BASE_URL}/search", params=params)
        resp.raise_for_status()

        data = resp.json()
        results = []
        for item in data:
            extra = item.get("extratags", {})
            address = item.get("address", {})
            results.append({
                "name": item.get("display_name", "").split(",")[0],
                "display_name": item.get("display_name", ""),
                "lat": item.get("lat", ""),
                "lon": item.get("lon", ""),
                "type": item.get("type", ""),
                "phone": extra.get("phone", extra.get("contact:phone", "")),
                "website": extra.get("website", extra.get("url", "")),
                "email": extra.get("email", extra.get("contact:email", "")),
                "address": _format_address(address),
                "osm_id": item.get("osm_id", ""),
                "osm_type": item.get("osm_type", ""),
            })

        return results

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class OSMSyncService:
    """OpenStreetMap Nominatim 同步封装（供 Celery 任务使用）"""

    BASE_URL = "https://nominatim.openstreetmap.org"

    def __init__(self):
        self._last_request_time: float = 0
        self._min_interval: float = 1.1

    def _rate_limit(self):
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def search_businesses(
        self,
        query: str,
        region: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """同步搜索本地商家"""
        self._rate_limit()

        search_query = query
        if region:
            search_query = f"{query}, {region}"

        params = {
            "q": search_query,
            "format": "json",
            "limit": min(limit, 50),
            "addressdetails": 1,
            "extratags": 1,
        }

        with httpx.Client(timeout=30.0, headers={"User-Agent": "GlobalLeads/1.0"}) as client:
            resp = client.get(f"{self.BASE_URL}/search", params=params)
            resp.raise_for_status()

        data = resp.json()
        results = []
        for item in data:
            extra = item.get("extratags", {})
            address = item.get("address", {})
            results.append({
                "name": item.get("display_name", "").split(",")[0],
                "display_name": item.get("display_name", ""),
                "lat": item.get("lat", ""),
                "lon": item.get("lon", ""),
                "type": item.get("type", ""),
                "phone": extra.get("phone", extra.get("contact:phone", "")),
                "website": extra.get("website", extra.get("url", "")),
                "email": extra.get("email", extra.get("contact:email", "")),
                "address": _format_address(address),
                "osm_id": item.get("osm_id", ""),
                "osm_type": item.get("osm_type", ""),
            })

        return results


def _format_address(address: dict) -> str:
    """格式化 OSM 地址信息"""
    parts = []
    for key in ["road", "house_number", "city", "state", "postcode", "country"]:
        if address.get(key):
            parts.append(address[key])
    return ", ".join(parts)
