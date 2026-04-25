"""
Apollo.io API 搜索公司服务

Apollo.io 提供公司搜索和联系人查找 API。
月度积分限制：900 积分/月。
"""
import time
import asyncio
from typing import Optional

import httpx

from app.core.config import settings


class ApolloService:
    """Apollo.io API 封装"""

    BASE_URL = "https://api.apollo.io/api/v1"

    def __init__(self):
        self.api_key = settings.APOLLO_API_KEY
        self._last_request_time: float = 0
        self._min_interval: float = 1.0  # 避免过快请求
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

    async def search_companies(
        self,
        industry: str | None = None,
        region: str | None = None,
        company_size: str | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict:
        """
        搜索公司

        Args:
            industry: 行业关键词
            region: 地区
            company_size: 公司规模（如 "11-50", "51-200"）
            page: 页码
            per_page: 每页数量

        Returns:
            包含公司列表和分页信息
        """
        await self._rate_limit()
        client = await self._get_client()

        payload = {
            "api_key": self.api_key,
            "page": page,
            "per_page": min(per_page, 100),
        }
        if industry:
            payload["industry"] = industry
        if region:
            payload["location"] = region
        if company_size:
            # Apollo 使用员工数范围
            size_map = {
                "1-10": "1,10",
                "11-50": "11,50",
                "51-200": "51,200",
                "201-500": "201,500",
                "501-1000": "501,1000",
            }
            payload["employee_ranges"] = [size_map.get(company_size, company_size)]

        resp = await client.post(
            f"{self.BASE_URL}/mixed_companies/search",
            json=payload,
        )
        resp.raise_for_status()

        data = resp.json()
        companies = []
        for org in data.get("organizations", []):
            companies.append({
                "id": org.get("id"),
                "company_name": org.get("name", ""),
                "website": org.get("website_url", ""),
                "company_size": org.get("employee_count", ""),
                "industry": org.get("industry", ""),
                "region": org.get("country", ""),
                "city": org.get("city", ""),
                "state": org.get("state", ""),
                "address": org.get("street_address", ""),
                "phone": org.get("phone", ""),
                "linkedin_url": org.get("linkedin_url", ""),
                "twitter_url": org.get("twitter_url", ""),
                "source": "apollo",
            })

        return {
            "total": data.get("pagination", {}).get("total_entries", 0),
            "page": page,
            "companies": companies,
        }

    async def get_contact_email(
        self,
        organization_id: str,
        title: str | None = None,
    ) -> list[dict]:
        """
        获取公司联系人邮箱

        Args:
            organization_id: Apollo 公司 ID
            title: 职位筛选关键词

        Returns:
            联系人列表
        """
        await self._rate_limit()
        client = await self._get_client()

        payload = {
            "api_key": self.api_key,
            "organization_ids": [organization_id],
            "per_page": 10,
        }
        if title:
            payload["person_titles"] = [title]

        resp = await client.post(
            f"{self.BASE_URL}/mixed_people/search",
            json=payload,
        )
        resp.raise_for_status()

        data = resp.json()
        contacts = []
        for person in data.get("people", []):
            contacts.append({
                "name": person.get("name", ""),
                "first_name": person.get("first_name", ""),
                "last_name": person.get("last_name", ""),
                "title": person.get("title", ""),
                "email": person.get("email", ""),
                "email_status": person.get("email_status", ""),
                "phone": person.get("phone_numbers", []),
                "linkedin_url": person.get("linkedin_url", ""),
                "source": "apollo",
            })

        return contacts

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class ApolloSyncService:
    """Apollo.io API 同步封装（供 Celery 任务使用）"""

    BASE_URL = "https://api.apollo.io/api/v1"

    def __init__(self):
        self.api_key = settings.APOLLO_API_KEY
        self._last_request_time: float = 0
        self._min_interval: float = 1.0

    def _rate_limit(self):
        """同步速率限制"""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def search_companies(
        self,
        industry: str | None = None,
        region: str | None = None,
        company_size: str | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict:
        """同步搜索公司"""
        self._rate_limit()

        payload = {
            "api_key": self.api_key,
            "page": page,
            "per_page": min(per_page, 100),
        }
        if industry:
            payload["industry"] = industry
        if region:
            payload["location"] = region
        if company_size:
            size_map = {
                "1-10": "1,10",
                "11-50": "11,50",
                "51-200": "51,200",
                "201-500": "201,500",
                "501-1000": "501,1000",
            }
            payload["employee_ranges"] = [size_map.get(company_size, company_size)]

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.BASE_URL}/mixed_companies/search",
                json=payload,
            )
            resp.raise_for_status()

        data = resp.json()
        companies = []
        for org in data.get("organizations", []):
            companies.append({
                "id": org.get("id"),
                "company_name": org.get("name", ""),
                "website": org.get("website_url", ""),
                "company_size": org.get("employee_count", ""),
                "industry": org.get("industry", ""),
                "region": org.get("country", ""),
                "city": org.get("city", ""),
                "state": org.get("state", ""),
                "address": org.get("street_address", ""),
                "phone": org.get("phone", ""),
                "linkedin_url": org.get("linkedin_url", ""),
                "source": "apollo",
            })

        return {
            "total": data.get("pagination", {}).get("total_entries", 0),
            "page": page,
            "companies": companies,
        }

    def get_contact_email(self, organization_id: str, title: str | None = None) -> list[dict]:
        """同步获取公司联系人邮箱"""
        self._rate_limit()

        payload = {
            "api_key": self.api_key,
            "organization_ids": [organization_id],
            "per_page": 10,
        }
        if title:
            payload["person_titles"] = [title]

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.BASE_URL}/mixed_people/search",
                json=payload,
            )
            resp.raise_for_status()

        data = resp.json()
        contacts = []
        for person in data.get("people", []):
            contacts.append({
                "name": person.get("name", ""),
                "first_name": person.get("first_name", ""),
                "last_name": person.get("last_name", ""),
                "title": person.get("title", ""),
                "email": person.get("email", ""),
                "email_status": person.get("email_status", ""),
                "phone": person.get("phone_numbers", []),
                "linkedin_url": person.get("linkedin_url", ""),
                "source": "apollo",
            })
        return contacts
