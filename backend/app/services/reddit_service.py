"""
Reddit API 搜索服务

使用 httpx async 调用 Reddit API，支持速率限制（60 请求/分钟）。
Reddit API 使用 OAuth2 认证，需要 client_id 和 client_secret。
"""
import time
import asyncio
from typing import Optional

import httpx

from app.core.config import settings


class RedditService:
    """Reddit API 封装"""

    BASE_URL = "https://www.reddit.com"
    OAUTH_URL = "https://oauth.reddit.com"

    def __init__(self):
        self.client_id = settings.REDDIT_CLIENT_ID
        self.client_secret = settings.REDDIT_CLIENT_SECRET
        self.user_agent = settings.REDDIT_USER_AGENT
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._last_request_time: float = 0
        self._min_interval: float = 1.0  # 60 requests/min = 1 request/sec
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 httpx 异步客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": self.user_agent},
            )
        return self._client

    async def _rate_limit(self):
        """速率限制：确保请求间隔 >= 1 秒"""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def _get_access_token(self) -> str:
        """获取 Reddit OAuth2 access token"""
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        client = await self._get_client()
        resp = await client.post(
            f"{self.BASE_URL}/api/v1/access_token",
            data={
                "grant_type": "client_credentials",
            },
            auth=(self.client_id, self.client_secret),
            headers={"User-Agent": self.user_agent},
        )
        resp.raise_for_status()
        data = resp.json()

        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self._token_expires_at = time.monotonic() + expires_in - 60  # 提前60秒过期

        return self._access_token

    async def search_posts(
        self,
        keyword: str,
        subreddit: str = "all",
        sort: str = "relevance",
        limit: int = 50,
        time_filter: str = "month",
    ) -> list[dict]:
        """
        搜索 Reddit 帖子

        Args:
            keyword: 搜索关键词
            subreddit: 子版块，默认 all
            sort: 排序方式 (relevance/hot/top/new/comments)
            limit: 返回数量限制
            time_filter: 时间范围 (hour/day/week/month/year/all)

        Returns:
            帖子列表，每个帖子包含 title, selftext, url, author 等字段
        """
        await self._rate_limit()

        token = await self._get_access_token()
        client = await self._get_client()

        params = {
            "q": keyword,
            "sort": sort,
            "limit": min(limit, 100),
            "t": time_filter,
            "type": "link",
        }

        resp = await client.get(
            f"{self.OAUTH_URL}/r/{subreddit}/search",
            params=params,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": self.user_agent,
            },
        )
        resp.raise_for_status()

        data = resp.json()
        posts = []
        for child in data.get("data", {}).get("children", []):
            post_data = child.get("data", {})
            posts.append({
                "id": post_data.get("id"),
                "title": post_data.get("title", ""),
                "content": post_data.get("selftext", ""),
                "author": post_data.get("author", "[deleted]"),
                "author_url": f"https://reddit.com/user/{post_data.get('author', '')}",
                "url": f"https://reddit.com{post_data.get('permalink', '')}",
                "subreddit": post_data.get("subreddit", ""),
                "score": post_data.get("score", 0),
                "num_comments": post_data.get("num_comments", 0),
                "created_utc": post_data.get("created_utc", 0),
                "published_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(post_data.get("created_utc", 0)),
                ) if post_data.get("created_utc") else None,
            })

        return posts

    async def get_post_comments(self, post_id: str, subreddit: str, limit: int = 30) -> list[dict]:
        """
        获取帖子评论

        Args:
            post_id: 帖子 ID
            subreddit: 子版块名称
            limit: 返回数量限制

        Returns:
            评论列表
        """
        await self._rate_limit()

        token = await self._get_access_token()
        client = await self._get_client()

        resp = await client.get(
            f"{self.OAUTH_URL}/r/{subreddit}/comments/{post_id}",
            params={"limit": limit, "sort": "top"},
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": self.user_agent,
            },
        )
        resp.raise_for_status()

        data = resp.json()
        comments = []

        def extract_comments(comment_list):
            for comment_data in comment_list:
                comment = comment_data.get("data", {})
                replies = comment.get("replies")
                comments.append({
                    "id": comment.get("id"),
                    "content": comment.get("body", ""),
                    "author": comment.get("author", "[deleted]"),
                    "author_url": f"https://reddit.com/user/{comment.get('author', '')}",
                    "score": comment.get("score", 0),
                    "created_utc": comment.get("created_utc", 0),
                    "published_at": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ",
                        time.gmtime(comment.get("created_utc", 0)),
                    ) if comment.get("created_utc") else None,
                })
                # 递归提取子评论
                if isinstance(replies, dict):
                    extract_comments(replies.get("data", {}).get("children", []))

        if len(data) > 1:
            listing = data[1].get("data", {}).get("children", [])
            extract_comments(listing)

        return comments

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class RedditSyncService:
    """Reddit API 同步封装（供 Celery 任务使用）"""

    BASE_URL = "https://www.reddit.com"
    OAUTH_URL = "https://oauth.reddit.com"

    def __init__(self):
        self.client_id = settings.REDDIT_CLIENT_ID
        self.client_secret = settings.REDDIT_CLIENT_SECRET
        self.user_agent = settings.REDDIT_USER_AGENT
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._last_request_time: float = 0
        self._min_interval: float = 1.0

    def _rate_limit(self):
        """同步速率限制"""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def _get_access_token(self) -> str:
        """获取 OAuth2 access token（同步）"""
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.BASE_URL}/api/v1/access_token",
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
                headers={"User-Agent": self.user_agent},
            )
            resp.raise_for_status()
            data = resp.json()

        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self._token_expires_at = time.monotonic() + expires_in - 60
        return self._access_token

    def search_posts(
        self,
        keyword: str,
        subreddit: str = "all",
        sort: str = "relevance",
        limit: int = 50,
        time_filter: str = "month",
    ) -> list[dict]:
        """同步搜索 Reddit 帖子"""
        self._rate_limit()
        token = self._get_access_token()

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{self.OAUTH_URL}/r/{subreddit}/search",
                params={
                    "q": keyword,
                    "sort": sort,
                    "limit": min(limit, 100),
                    "t": time_filter,
                    "type": "link",
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": self.user_agent,
                },
            )
            resp.raise_for_status()

        data = resp.json()
        posts = []
        for child in data.get("data", {}).get("children", []):
            post_data = child.get("data", {})
            posts.append({
                "id": post_data.get("id"),
                "title": post_data.get("title", ""),
                "content": post_data.get("selftext", ""),
                "author": post_data.get("author", "[deleted]"),
                "author_url": f"https://reddit.com/user/{post_data.get('author', '')}",
                "url": f"https://reddit.com{post_data.get('permalink', '')}",
                "subreddit": post_data.get("subreddit", ""),
                "score": post_data.get("score", 0),
                "num_comments": post_data.get("num_comments", 0),
                "created_utc": post_data.get("created_utc", 0),
                "published_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(post_data.get("created_utc", 0)),
                ) if post_data.get("created_utc") else None,
            })

        return posts

    def get_post_comments(self, post_id: str, subreddit: str, limit: int = 30) -> list[dict]:
        """同步获取帖子评论"""
        self._rate_limit()
        token = self._get_access_token()

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{self.OAUTH_URL}/r/{subreddit}/comments/{post_id}",
                params={"limit": limit, "sort": "top"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": self.user_agent,
                },
            )
            resp.raise_for_status()

        data = resp.json()
        comments = []

        def extract_comments(comment_list):
            for comment_data in comment_list:
                comment = comment_data.get("data", {})
                replies = comment.get("replies")
                comments.append({
                    "id": comment.get("id"),
                    "content": comment.get("body", ""),
                    "author": comment.get("author", "[deleted]"),
                    "author_url": f"https://reddit.com/user/{comment.get('author', '')}",
                    "score": comment.get("score", 0),
                    "created_utc": comment.get("created_utc", 0),
                    "published_at": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ",
                        time.gmtime(comment.get("created_utc", 0)),
                    ) if comment.get("created_utc") else None,
                })
                if isinstance(replies, dict):
                    extract_comments(replies.get("data", {}).get("children", []))

        if len(data) > 1:
            listing = data[1].get("data", {}).get("children", [])
            extract_comments(listing)

        return comments
