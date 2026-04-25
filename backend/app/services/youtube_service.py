"""
YouTube Data API v3 搜索服务

使用 httpx async 调用 YouTube API，每日配额 10000 单位。
搜索一次消耗约 100 单位。
"""
import time
import asyncio
from typing import Optional

import httpx

from app.core.config import settings


class YouTubeService:
    """YouTube Data API v3 封装"""

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self):
        self.api_key = settings.YOUTUBE_API_KEY
        self._last_request_time: float = 0
        self._min_interval: float = 0.5  # 避免过快请求
        self._daily_quota_used: int = 0
        self._quota_reset_date: str = ""
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

    def _check_daily_quota(self, cost: int = 100) -> bool:
        """
        检查每日配额

        Args:
            cost: 本次请求消耗的配额单位

        Returns:
            是否还有配额
        """
        today = time.strftime("%Y-%m-%d")
        if self._quota_reset_date != today:
            self._daily_quota_used = 0
            self._quota_reset_date = today

        if self._daily_quota_used + cost > 10000:
            return False

        self._daily_quota_used += cost
        return True

    async def search_videos(
        self,
        keyword: str,
        max_results: int = 25,
        order: str = "relevance",
        published_after: str | None = None,
        region_code: str | None = None,
    ) -> list[dict]:
        """
        搜索 YouTube 视频

        Args:
            keyword: 搜索关键词
            max_results: 返回数量限制（最大50）
            order: 排序方式 (date/rating/relevance/title/videoCount/viewCount)
            published_after: 发布时间后（RFC 3339 格式）
            region_code: 区域代码

        Returns:
            视频列表
        """
        if not self._check_daily_quota(cost=100):
            raise RuntimeError("YouTube API 每日配额已用完")

        await self._rate_limit()
        client = await self._get_client()

        params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "maxResults": min(max_results, 50),
            "order": order,
            "key": self.api_key,
        }
        if published_after:
            params["publishedAfter"] = published_after
        if region_code:
            params["regionCode"] = region_code

        resp = await client.get(f"{self.BASE_URL}/search", params=params)
        resp.raise_for_status()

        data = resp.json()
        videos = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            videos.append({
                "id": item.get("id", {}).get("videoId", ""),
                "title": snippet.get("title", ""),
                "content": snippet.get("description", ""),
                "channel": snippet.get("channelTitle", ""),
                "channel_url": f"https://www.youtube.com/channel/{snippet.get('channelId', '')}",
                "url": f"https://www.youtube.com/watch?v={item.get('id', {}).get('videoId', '')}",
                "published_at": snippet.get("publishedAt", ""),
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            })

        return videos

    async def get_video_comments(
        self,
        video_id: str,
        max_results: int = 30,
        order: str = "relevance",
    ) -> list[dict]:
        """
        获取视频评论

        Args:
            video_id: 视频 ID
            max_results: 返回数量限制
            order: 排序方式 (relevance/time)

        Returns:
            评论列表
        """
        if not self._check_daily_quota(cost=1):
            raise RuntimeError("YouTube API 每日配额已用完")

        await self._rate_limit()
        client = await self._get_client()

        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(max_results, 100),
            "order": order,
            "textFormat": "plainText",
            "key": self.api_key,
        }

        resp = await client.get(f"{self.BASE_URL}/commentThreads", params=params)
        resp.raise_for_status()

        data = resp.json()
        comments = []
        for item in data.get("items", []):
            top_comment = item.get("snippet", {}).get("topLevelComment", {})
            comment_snippet = top_comment.get("snippet", {})
            comments.append({
                "id": top_comment.get("id", ""),
                "content": comment_snippet.get("textDisplay", ""),
                "author": comment_snippet.get("authorDisplayName", ""),
                "author_url": comment_snippet.get("authorChannelUrl", ""),
                "like_count": comment_snippet.get("likeCount", 0),
                "published_at": comment_snippet.get("publishedAt", ""),
                "video_id": video_id,
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
            })

        return comments

    @property
    def daily_quota_used(self) -> int:
        """获取今日已用配额"""
        today = time.strftime("%Y-%m-%d")
        if self._quota_reset_date != today:
            return 0
        return self._daily_quota_used

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class YouTubeSyncService:
    """YouTube API 同步封装（供 Celery 任务使用）"""

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self):
        self.api_key = settings.YOUTUBE_API_KEY
        self._last_request_time: float = 0
        self._min_interval: float = 0.5
        self._daily_quota_used: int = 0
        self._quota_reset_date: str = ""

    def _rate_limit(self):
        """同步速率限制"""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def _check_daily_quota(self, cost: int = 100) -> bool:
        today = time.strftime("%Y-%m-%d")
        if self._quota_reset_date != today:
            self._daily_quota_used = 0
            self._quota_reset_date = today
        if self._daily_quota_used + cost > 10000:
            return False
        self._daily_quota_used += cost
        return True

    def search_videos(self, keyword: str, max_results: int = 25, order: str = "relevance") -> list[dict]:
        """同步搜索 YouTube 视频"""
        if not self._check_daily_quota(cost=100):
            raise RuntimeError("YouTube API 每日配额已用完")

        self._rate_limit()

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{self.BASE_URL}/search",
                params={
                    "part": "snippet",
                    "q": keyword,
                    "type": "video",
                    "maxResults": min(max_results, 50),
                    "order": order,
                    "key": self.api_key,
                },
            )
            resp.raise_for_status()

        data = resp.json()
        videos = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            videos.append({
                "id": item.get("id", {}).get("videoId", ""),
                "title": snippet.get("title", ""),
                "content": snippet.get("description", ""),
                "channel": snippet.get("channelTitle", ""),
                "channel_url": f"https://www.youtube.com/channel/{snippet.get('channelId', '')}",
                "url": f"https://www.youtube.com/watch?v={item.get('id', {}).get('videoId', '')}",
                "published_at": snippet.get("publishedAt", ""),
            })
        return videos

    def get_video_comments(self, video_id: str, max_results: int = 30) -> list[dict]:
        """同步获取视频评论"""
        if not self._check_daily_quota(cost=1):
            raise RuntimeError("YouTube API 每日配额已用完")

        self._rate_limit()

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{self.BASE_URL}/commentThreads",
                params={
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": min(max_results, 100),
                    "order": "relevance",
                    "textFormat": "plainText",
                    "key": self.api_key,
                },
            )
            resp.raise_for_status()

        data = resp.json()
        comments = []
        for item in data.get("items", []):
            top_comment = item.get("snippet", {}).get("topLevelComment", {})
            cs = top_comment.get("snippet", {})
            comments.append({
                "id": top_comment.get("id", ""),
                "content": cs.get("textDisplay", ""),
                "author": cs.get("authorDisplayName", ""),
                "author_url": cs.get("authorChannelUrl", ""),
                "like_count": cs.get("likeCount", 0),
                "published_at": cs.get("publishedAt", ""),
                "video_id": video_id,
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
            })
        return comments
