"""
请求日志中间件

自动记录每个 API 请求：
- 请求方法、路径、状态码、耗时
- 认证用户（如已登录）
- 请求追踪 ID（request_id）

日志示例：
  INFO api.access: GET /api/v1/dashboard/stats 200 12ms user=admin request_id=a1b2c3
  INFO api.access: POST /api/v1/auth/login 200 89ms request_id=d4e5f6
  WARNING api.access: POST /api/v1/auth/login 401 - user=unknown request_id=g7h8i9
"""
import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api.access")

# 不记录的路径（健康检查、文档等）
SKIP_PATHS = {"/", "/docs", "/redoc", "/openapi.json", "/nginx-health", "/favicon.ico"}


def _short_id() -> str:
    """生成 8 位短 ID 用于请求追踪"""
    return uuid.uuid4().hex[:8]


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next) -> Response:
        # 跳过不需要记录的路径
        path = request.url.path
        if path in SKIP_PATHS or path.startswith("/assets"):
            return await call_next(request)

        request_id = _short_id()
        start_time = time.time()

        # 将 request_id 存入 request state，供其他地方使用
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            duration_ms = int((time.time() - start_time) * 1000)

            # 尝试获取当前用户（从 Authorization header 解析，不查库）
            user_info = self._get_user_hint(request)

            # 构建日志消息
            msg = (
                f"{request.method} {path} {response.status_code} {duration_ms}ms"
                f" request_id={request_id}"
            )
            if user_info:
                msg += f" user={user_info}"

            if response.status_code >= 500:
                logger.error(msg)
            elif response.status_code >= 400:
                logger.warning(msg)
            else:
                logger.info(msg)

            # 在响应头中返回 request_id，方便前端排查问题
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "%s %s 500 %dms request_id=%s error=%s",
                request.method, path, duration_ms, request_id, str(e),
                exc_info=True,
            )
            raise

    @staticmethod
    def _get_user_hint(request: Request) -> str:
        """从请求中提取用户标识（轻量，不查数据库）"""
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer ") and len(auth) > 20:
            # 不记录 token，只返回 "authenticated"
            return "authenticated"
        return ""
