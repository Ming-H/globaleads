"""
Bluesky AT Protocol API 搜索服务

使用 httpx async 调用 Bluesky API，支持速率限制（3000 请求/5 分钟）。
Bluesky 使用 AT Protocol 的 xrpc 接口。
"""
import time
import asyncio
from typing import Optional

import httpx

from app.core.config import settings


class BlueskyService:
    """Bluesky API 封装"""

    BASE_URL = "https://bsky.social"
    XRPC_URL = "https://bsky.social/xrpc"

    def __init__(self):
        self.handle = settings.BLUESKY_HANDLE
        self.password = settings.BLUESKY_PASSWORD
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._last_request_time: float = 0
        self._min_interval: float = 0.1  # 3000/5min = 600/min = 10/sec
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

    async def _authenticate(self) -> str:
        """Bluesky 认证，获取 access token"""
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        client = await self._get_client()
        resp = await client.post(
            f"{self.XRPC_URL}/com.atproto.server.createSession",
            json={
                "identifier": self.handle,
                "password": self.password,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        self._access_token = data["accessJwt"]
        self._refresh_token = data.get("refreshJwt")
        self._token_expires_at = time.monotonic() + 7200  # 约2小时

        return self._access_token

    async def search_posts(
        self,
        keyword: str,
        limit: int = 50,
        sort: str = "latest",
        since: str | None = None,
        until: str | None = None,
    ) -> list[dict]:
        """
        搜索 Bluesky 帖子

        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            sort: 排序方式 (latest/top)
            since: 起始时间 ISO 格式
            until: 结束时间 ISO 格式

        Returns:
            帖子列表
        """
        await self._rate_limit()

        token = await self._authenticate()
        client = await self._get_client()

        params = {
            "q": keyword,
            "limit": min(limit, 100),
            "sort": sort,
        }
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        resp = await client.get(
            f"{self.XRPC_URL}/app.bsky.feed.searchPosts",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()

        data = resp.json()
        posts = []
        for item in data.get("posts", []):
            record = item.get("record", {})
            author = item.get("author", {})

            # 解析内容中的嵌入链接
            content = record.get("text", "")
            facets = record.get("facets", [])

            posts.append({
                "id": item.get("uri", "").split("/")[-1] if item.get("uri") else "",
                "uri": item.get("uri", ""),
                "content": content,
                "author": author.get("handle", ""),
                "author_display_name": author.get("displayName", ""),
                "author_url": f"https://bsky.app/profile/{author.get('handle', '')}",
                "url": f"https://bsky.app/profile/{author.get('handle', '')}/post/{item.get('uri', '').split('/')[-1]}" if item.get("uri") else "",
                "like_count": item.get("likeCount", 0),
                "reply_count": item.get("replyCount", 0),
                "repost_count": item.get("repostCount", 0),
                "indexed_at": item.get("indexedAt", ""),
                "published_at": record.get("createdAt", ""),
                "facets": facets,
            })

        return posts

    async def get_post_thread(self, uri: str, depth: int = 5) -> list[dict]:
        """
        获取帖子评论线程

        Args:
            uri: 帖子 AT URI
            depth: 线程深度

        Returns:
            回复列表
        """
        await self._rate_limit()

        token = await self._authenticate()
        client = await self._get_client()

        resp = await client.get(
            f"{self.XRPC_URL}/app.bsky.feed.getPostThread",
            params={"uri": uri, "depth": depth},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()

        data = resp.json()
        replies = []

        def extract_replies(thread_data):
            for reply in thread_data.get("replies", []):
                post = reply.get("post", {})
                record = post.get("record", {})
                author = post.get("author", {})
                replies.append({
                    "id": post.get("uri", "").split("/")[-1],
                    "uri": post.get("uri", ""),
                    "content": record.get("text", ""),
                    "author": author.get("handle", ""),
                    "author_display_name": author.get("displayName", ""),
                    "author_url": f"https://bsky.app/profile/{author.get('handle', '')}",
                    "like_count": post.get("likeCount", 0),
                    "published_at": record.get("createdAt", ""),
                })
                extract_replies(reply)

        thread = data.get("thread", {})
        extract_replies(thread)

        return replies

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class BlueskySyncService:
    """Bluesky API 同步封装（供 Celery 任务使用）"""

    XRPC_URL = "https://bsky.social/xrpc"

    def __init__(self):
        self.handle = settings.BLUESKY_HANDLE
        self.password = settings.BLUESKY_PASSWORD
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._last_request_time: float = 0
        self._min_interval: float = 0.1

    def _rate_limit(self):
        """同步速率限制"""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def _authenticate(self) -> str:
        """同步认证"""
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.XRPC_URL}/com.atproto.server.createSession",
                json={"identifier": self.handle, "password": self.password},
            )
            resp.raise_for_status()
            data = resp.json()

        self._access_token = data["accessJwt"]
        self._token_expires_at = time.monotonic() + 7200
        return self._access_token

    def search_posts(self, keyword: str, limit: int = 50, sort: str = "latest") -> list[dict]:
        """同步搜索 Bluesky 帖子"""
        self._rate_limit()
        token = self._authenticate()

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{self.XRPC_URL}/app.bsky.feed.searchPosts",
                params={"q": keyword, "limit": min(limit, 100), "sort": sort},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()

        data = resp.json()
        posts = []
        for item in data.get("posts", []):
            record = item.get("record", {})
            author = item.get("author", {})
            posts.append({
                "id": item.get("uri", "").split("/")[-1] if item.get("uri") else "",
                "uri": item.get("uri", ""),
                "content": record.get("text", ""),
                "author": author.get("handle", ""),
                "author_display_name": author.get("displayName", ""),
                "author_url": f"https://bsky.app/profile/{author.get('handle', '')}",
                "url": f"https://bsky.app/profile/{author.get('handle', '')}/post/{item.get('uri', '').split('/')[-1]}" if item.get("uri") else "",
                "like_count": item.get("likeCount", 0),
                "reply_count": item.get("replyCount", 0),
                "published_at": record.get("createdAt", ""),
            })
        return posts
