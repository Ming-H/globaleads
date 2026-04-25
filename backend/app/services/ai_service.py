"""
AI 分析服务

统一使用 OpenAI 兼容接口格式，支持 Ollama / DeepSeek 切换。
通过 AI_PROVIDER 环境变量控制使用哪个提供商。
"""
import json
import logging
import time
import asyncio
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """AI 分析服务（支持 Ollama / DeepSeek 切换）"""

    def __init__(self):
        self.base_url = settings.ai_base_url
        self.api_key = settings.ai_api_key
        self.model = settings.ai_model
        self.provider = settings.AI_PROVIDER
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 httpx 异步客户端"""
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=60.0,
                headers=headers,
            )
        return self._client

    async def _call_llm(self, messages: list[dict], temperature: float = 0.1) -> str:
        """
        调用 LLM API（OpenAI 兼容接口）

        Args:
            messages: 消息列表
            temperature: 温度参数

        Returns:
            模型回复文本
        """
        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2000,
        }

        # Ollama 和 DeepSeek 都使用 /v1/chat/completions 端点
        endpoint = "/v1/chat/completions"

        try:
            resp = await client.post(endpoint, json=payload)
            resp.raise_for_status()

            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip()
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API 调用失败: status={e.response.status_code}, body={e.response.text}")
            raise
        except Exception as e:
            logger.error(f"LLM API 调用异常: {e}")
            raise

    def _build_intent_prompt(self, content: str, keywords: list[str]) -> list[dict]:
        """
        构建购买意向分析 prompt

        Args:
            content: 要分析的文本内容
            keywords: 搜索使用的关键词列表

        Returns:
            消息列表
        """
        keywords_str = ", ".join(keywords)
        system_prompt = f"""你是一个专业的海外销售线索分析助手。你的任务是分析社交媒体帖子和评论，判断其中是否包含购买/求购意向。

搜索关键词：{keywords_str}

请分析以下内容，返回 JSON 格式的结果：
{{
    "has_intent": true/false,
    "score": 1-100的评分（100表示购买意向最强）,
    "tags": ["标签1", "标签2"],
    "analysis": "详细分析说明"
}}

评分标准：
- 90-100：明确表达购买需求，包含具体产品要求和联系方式
- 70-89：有较强购买意向，提到需求但不够具体
- 50-69：可能有意向，需要进一步确认
- 30-49：兴趣不大，只是泛泛讨论
- 0-29：完全无关或没有购买意向

标签选项：求购、找供应商、询价、比价、问推荐、找替代品、合作、代理、其他

注意：
1. 只返回 JSON，不要额外解释
2. tags 是中文标签数组
3. 如果内容不是英文，请先理解内容再分析"""

        user_prompt = f"请分析以下内容：\n\n{content}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _parse_intent_response(self, response: str) -> dict:
        """
        解析 AI 返回的意向分析结果

        Args:
            response: AI 返回的文本

        Returns:
            解析后的结果字典
        """
        try:
            # 尝试提取 JSON 部分
            json_str = response
            # 处理 markdown 代码块包裹的 JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()

            result = json.loads(json_str)
            return {
                "has_intent": bool(result.get("has_intent", False)),
                "score": min(100, max(0, int(result.get("score", 0)))),
                "tags": result.get("tags", []),
                "analysis": result.get("analysis", ""),
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"AI 响应解析失败: {e}, response={response[:200]}")
            return {
                "has_intent": False,
                "score": 0,
                "tags": [],
                "analysis": f"解析失败: {str(e)}",
            }

    async def analyze_purchase_intent(
        self,
        content: str,
        keywords: list[str],
    ) -> dict:
        """
        分析内容是否有购买意向

        Args:
            content: 要分析的文本内容
            keywords: 搜索使用的关键词列表

        Returns:
            {"has_intent": bool, "score": int, "tags": list[str], "analysis": str}
        """
        messages = self._build_intent_prompt(content, keywords)
        response = await self._call_llm(messages)
        return self._parse_intent_response(response)

    async def batch_analyze(
        self,
        items: list[dict],
        keywords: list[str],
        content_key: str = "content",
        batch_size: int = 5,
    ) -> list[dict]:
        """
        批量分析购买意向

        Args:
            items: 待分析项列表
            keywords: 关键词列表
            content_key: 内容字段名
            batch_size: 并发批次大小

        Returns:
            每个项添加 ai_result 字段的结果列表
        """
        results = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            tasks = [
                self.analyze_purchase_intent(item.get(content_key, ""), keywords)
                for item in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for item, ai_result in zip(batch, batch_results):
                if isinstance(ai_result, Exception):
                    logger.error(f"AI 分析失败: {ai_result}")
                    results.append({
                        **item,
                        "ai_result": {
                            "has_intent": False,
                            "score": 0,
                            "tags": [],
                            "analysis": f"分析失败: {str(ai_result)}",
                        },
                    })
                else:
                    results.append({**item, "ai_result": ai_result})

            # 批次间短暂暂停，避免速率限制
            if i + batch_size < len(items):
                await asyncio.sleep(0.5)

        return results

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class AISyncService:
    """AI 分析服务同步封装（供 Celery 任务使用）"""

    def __init__(self):
        self.base_url = settings.ai_base_url
        self.api_key = settings.ai_api_key
        self.model = settings.ai_model

    def _call_llm(self, messages: list[dict], temperature: float = 0.1) -> str:
        """同步调用 LLM API"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2000,
        }

        with httpx.Client(base_url=self.base_url, timeout=60.0, headers=headers) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            resp.raise_for_status()

        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

    def _build_intent_prompt(self, content: str, keywords: list[str]) -> list[dict]:
        """构建购买意向分析 prompt"""
        keywords_str = ", ".join(keywords)
        system_prompt = f"""你是一个专业的海外销售线索分析助手。你的任务是分析社交媒体帖子和评论，判断其中是否包含购买/求购意向。

搜索关键词：{keywords_str}

请分析以下内容，返回 JSON 格式的结果：
{{
    "has_intent": true/false,
    "score": 1-100的评分（100表示购买意向最强）,
    "tags": ["标签1", "标签2"],
    "analysis": "详细分析说明"
}}

评分标准：
- 90-100：明确表达购买需求
- 70-89：有较强购买意向
- 50-69：可能有意向
- 30-49：兴趣不大
- 0-29：完全无关

标签选项：求购、找供应商、询价、比价、问推荐、找替代品、合作、代理、其他

只返回 JSON，不要额外解释。"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下内容：\n\n{content}"},
        ]

    def _parse_intent_response(self, response: str) -> dict:
        """解析 AI 返回结果"""
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()

            result = json.loads(json_str)
            return {
                "has_intent": bool(result.get("has_intent", False)),
                "score": min(100, max(0, int(result.get("score", 0)))),
                "tags": result.get("tags", []),
                "analysis": result.get("analysis", ""),
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"AI 响应解析失败: {e}")
            return {
                "has_intent": False,
                "score": 0,
                "tags": [],
                "analysis": f"解析失败: {str(e)}",
            }

    def analyze_purchase_intent(self, content: str, keywords: list[str]) -> dict:
        """同步分析购买意向"""
        messages = self._build_intent_prompt(content, keywords)
        response = self._call_llm(messages)
        return self._parse_intent_response(response)
