"""
Google Maps Places API 搜索服务

用于搜索本地商家信息。月度限制：6250 次请求。
"""
import time
import asyncio
from typing import Optional

import httpx

from app.core.config import settings


class GoogleMapsService:
    """Google Maps Places API 封装"""

    BASE_URL = "https://maps.googleapis.com/maps/api/place"

    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        self._last_request_time: float = 0
        self._min_interval: float = 0.5
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 httpx 异步客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _rate_limit(self):
        """速率限制"""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def search_places(
        self,
        query: str,
        location: str | None = None,
        radius: int = 50000,
        region: str | None = None,
        language: str = "en",
    ) -> list[dict]:
        """
        搜索地点（Text Search）

        Args:
            query: 搜索关键词（如 "LED lighting distributor"）
            location: 中心坐标 "lat,lng"
            radius: 搜索半径（米）
            region: 区域代码
            language: 语言代码

        Returns:
            地点列表
        """
        await self._rate_limit()
        client = await self._get_client()

        params = {
            "query": query,
            "key": self.api_key,
            "language": language,
        }
        if location:
            params["location"] = location
            params["radius"] = radius
        if region:
            params["region"] = region

        resp = await client.get(f"{self.BASE_URL}/textsearch/json", params=params)
        resp.raise_for_status()

        data = resp.json()
        places = []
        for place in data.get("results", []):
            places.append({
                "place_id": place.get("place_id", ""),
                "company_name": place.get("name", ""),
                "company_address": place.get("formatted_address", ""),
                "region": place.get("formatted_address", "").split(",")[-1].strip() if place.get("formatted_address") else "",
                "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                "lng": place.get("geometry", {}).get("location", {}).get("lng"),
                "rating": place.get("rating", 0),
                "user_ratings_total": place.get("user_ratings_total", 0),
                "types": place.get("types", []),
                "phone": place.get("formatted_phone_number", ""),
                "website": place.get("website", ""),
                "source": "google_maps",
            })

        return places

    async def get_place_details(self, place_id: str) -> dict:
        """
        获取地点详情（含电话、网站等）

        Args:
            place_id: Google Place ID

        Returns:
            地点详情
        """
        await self._rate_limit()
        client = await self._get_client()

        params = {
            "place_id": place_id,
            "key": self.api_key,
            "fields": "name,formatted_address,formatted_phone_number,website,url,rating,user_ratings_total,international_phone_number",
        }

        resp = await client.get(f"{self.BASE_URL}/details/json", params=params)
        resp.raise_for_status()

        data = resp.json()
        result = data.get("result", {})

        return {
            "place_id": place_id,
            "company_name": result.get("name", ""),
            "company_address": result.get("formatted_address", ""),
            "phone": result.get("formatted_phone_number", "") or result.get("international_phone_number", ""),
            "website": result.get("website", ""),
            "url": result.get("url", ""),
            "rating": result.get("rating", 0),
            "user_ratings_total": result.get("user_ratings_total", 0),
            "source": "google_maps",
        }

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class GoogleMapsSyncService:
    """Google Maps API 同步封装（供 Celery 任务使用）"""

    BASE_URL = "https://maps.googleapis.com/maps/api/place"

    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        self._last_request_time: float = 0
        self._min_interval: float = 0.5

    def _rate_limit(self):
        """同步速率限制"""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def search_places(
        self,
        query: str,
        location: str | None = None,
        radius: int = 50000,
        region: str | None = None,
    ) -> list[dict]:
        """同步搜索地点"""
        self._rate_limit()

        params = {
            "query": query,
            "key": self.api_key,
            "language": "en",
        }
        if location:
            params["location"] = location
            params["radius"] = radius
        if region:
            params["region"] = region

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{self.BASE_URL}/textsearch/json", params=params)
            resp.raise_for_status()

        data = resp.json()
        places = []
        for place in data.get("results", []):
            places.append({
                "place_id": place.get("place_id", ""),
                "company_name": place.get("name", ""),
                "company_address": place.get("formatted_address", ""),
                "region": place.get("formatted_address", "").split(",")[-1].strip() if place.get("formatted_address") else "",
                "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                "lng": place.get("geometry", {}).get("location", {}).get("lng"),
                "rating": place.get("rating", 0),
                "types": place.get("types", []),
                "source": "google_maps",
            })
        return places

    def get_place_details(self, place_id: str) -> dict:
        """同步获取地点详情"""
        self._rate_limit()

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{self.BASE_URL}/details/json",
                params={
                    "place_id": place_id,
                    "key": self.api_key,
                    "fields": "name,formatted_address,formatted_phone_number,website,url,rating",
                },
            )
            resp.raise_for_status()

        data = resp.json()
        result = data.get("result", {})
        return {
            "place_id": place_id,
            "company_name": result.get("name", ""),
            "company_address": result.get("formatted_address", ""),
            "phone": result.get("formatted_phone_number", ""),
            "website": result.get("website", ""),
            "url": result.get("url", ""),
            "source": "google_maps",
        }
