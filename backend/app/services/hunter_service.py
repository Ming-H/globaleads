"""
Hunter.io 邮箱查找服务

Hunter.io 提供域名邮箱查找和验证功能。
月度限制：25 积分/月。
"""
import time
import asyncio
from typing import Optional

import httpx

from app.core.config import settings


class HunterService:
    """Hunter.io API 封装"""

    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self):
        self.api_key = settings.HUNTER_API_KEY
        self._last_request_time: float = 0
        self._min_interval: float = 2.0  # 避免过快请求
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

    async def domain_search(
        self,
        domain: str,
        limit: int = 10,
        department: str | None = None,
        seniority: str | None = None,
    ) -> list[dict]:
        """
        根据域名查找邮箱

        Args:
            domain: 公司域名（如 "example.com"）
            limit: 返回数量限制
            department: 部门筛选 (executive/it/finance... )
            seniority: 职级筛选 (junior/senior/manager/director... )

        Returns:
            邮箱列表
        """
        await self._rate_limit()
        client = await self._get_client()

        params = {
            "domain": domain,
            "api_key": self.api_key,
            "limit": min(limit, 100),
        }
        if department:
            params["department"] = department
        if seniority:
            params["seniority"] = seniority

        resp = await client.get(f"{self.BASE_URL}/domain-search", params=params)
        resp.raise_for_status()

        data = resp.json()
        emails = []
        for email_data in data.get("data", {}).get("emails", []):
            emails.append({
                "email": email_data.get("value", ""),
                "type": email_data.get("type", ""),
                "confidence": email_data.get("confidence", 0),
                "first_name": email_data.get("first_name", ""),
                "last_name": email_data.get("last_name", ""),
                "full_name": email_data.get("first_name", "") + " " + email_data.get("last_name", ""),
                "position": email_data.get("position", ""),
                "department": email_data.get("department", ""),
                "phone_number": email_data.get("phone_number", ""),
                "linkedin_url": email_data.get("linkedin", ""),
                "twitter_url": email_data.get("twitter", ""),
                "sources": [s.get("uri", "") for s in email_data.get("sources", [])],
                "verified": email_data.get("verification", {}).get("status") == "valid",
            })

        return emails

    async def email_finder(
        self,
        domain: str,
        first_name: str,
        last_name: str,
    ) -> dict | None:
        """
        查找特定联系人的邮箱

        Args:
            domain: 公司域名
            first_name: 名
            last_name: 姓

        Returns:
            邮箱信息或 None
        """
        await self._rate_limit()
        client = await self._get_client()

        params = {
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
            "api_key": self.api_key,
        }

        resp = await client.get(f"{self.BASE_URL}/email-finder", params=params)
        resp.raise_for_status()

        data = resp.json()
        email_data = data.get("data", {})

        if not email_data or not email_data.get("email"):
            return None

        return {
            "email": email_data.get("email", ""),
            "score": email_data.get("score", 0),
            "first_name": email_data.get("first_name", ""),
            "last_name": email_data.get("last_name", ""),
            "position": email_data.get("position", ""),
            "phone_number": email_data.get("phone_number", ""),
            "verified": email_data.get("verification", {}).get("status") == "valid",
        }

    async def verify_email(self, email: str) -> dict:
        """
        验证邮箱是否有效

        Args:
            email: 邮箱地址

        Returns:
            验证结果
        """
        await self._rate_limit()
        client = await self._get_client()

        params = {
            "email": email,
            "api_key": self.api_key,
        }

        resp = await client.get(f"{self.BASE_URL}/email-verifier", params=params)
        resp.raise_for_status()

        data = resp.json()
        result = data.get("data", {})

        return {
            "email": email,
            "result": result.get("result", ""),
            "score": result.get("score", 0),
            "regexp": result.get("regexp", False),
            "smtp": result.get("smtp", False),
            "smtp_check": result.get("smtp_check", False),
            "accept_all": result.get("accept_all", False),
            "disposable": result.get("disposable", False),
            "webmail": result.get("webmail", False),
            "is_valid": result.get("result") == "deliverable",
        }

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class HunterSyncService:
    """Hunter.io API 同步封装（供 Celery 任务使用）"""

    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self):
        self.api_key = settings.HUNTER_API_KEY
        self._last_request_time: float = 0
        self._min_interval: float = 2.0

    def _rate_limit(self):
        """同步速率限制"""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def domain_search(
        self,
        domain: str,
        limit: int = 10,
        department: str | None = None,
    ) -> list[dict]:
        """同步根据域名查找邮箱"""
        self._rate_limit()

        params = {
            "domain": domain,
            "api_key": self.api_key,
            "limit": min(limit, 100),
        }
        if department:
            params["department"] = department

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{self.BASE_URL}/domain-search", params=params)
            resp.raise_for_status()

        data = resp.json()
        emails = []
        for email_data in data.get("data", {}).get("emails", []):
            emails.append({
                "email": email_data.get("value", ""),
                "type": email_data.get("type", ""),
                "confidence": email_data.get("confidence", 0),
                "first_name": email_data.get("first_name", ""),
                "last_name": email_data.get("last_name", ""),
                "full_name": email_data.get("first_name", "") + " " + email_data.get("last_name", ""),
                "position": email_data.get("position", ""),
                "department": email_data.get("department", ""),
                "phone_number": email_data.get("phone_number", ""),
                "sources": [s.get("uri", "") for s in email_data.get("sources", [])],
                "verified": email_data.get("verification", {}).get("status") == "valid",
            })
        return emails

    def email_finder(self, domain: str, first_name: str, last_name: str) -> dict | None:
        """同步查找特定联系人邮箱"""
        self._rate_limit()

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{self.BASE_URL}/email-finder",
                params={
                    "domain": domain,
                    "first_name": first_name,
                    "last_name": last_name,
                    "api_key": self.api_key,
                },
            )
            resp.raise_for_status()

        data = resp.json()
        email_data = data.get("data", {})
        if not email_data or not email_data.get("email"):
            return None

        return {
            "email": email_data.get("email", ""),
            "score": email_data.get("score", 0),
            "first_name": email_data.get("first_name", ""),
            "last_name": email_data.get("last_name", ""),
            "position": email_data.get("position", ""),
            "verified": email_data.get("verification", {}).get("status") == "valid",
        }

    def verify_email(self, email: str) -> dict:
        """同步验证邮箱"""
        self._rate_limit()

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{self.BASE_URL}/email-verifier",
                params={"email": email, "api_key": self.api_key},
            )
            resp.raise_for_status()

        data = resp.json()
        result = data.get("data", {})
        return {
            "email": email,
            "result": result.get("result", ""),
            "score": result.get("score", 0),
            "is_valid": result.get("result") == "deliverable",
        }
