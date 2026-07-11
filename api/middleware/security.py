"""
API 安全中间件。

提供基于 API Key 的认证与基于内存的滑动窗口限流。
"""

import asyncio
import hmac
import os
import time
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    API Key 认证中间件。

    通过环境变量 ``GREENVRP_API_KEY`` 配置密钥。若未配置且未显式设置
    ``GREENVRP_ALLOW_UNAUTHENTICATED=true``，则对健康检查外的所有请求返回 401，
    实现默认"失败关闭"。
    健康检查端点（/api/v1/health、/api/v1/）始终放行，便于负载均衡探测。
    """

    def __init__(self, app, api_key: str | None = None):
        super().__init__(app)
        self.api_key = api_key or os.getenv("GREENVRP_API_KEY")
        self.allow_unauthenticated = (
            os.getenv("GREENVRP_ALLOW_UNAUTHENTICATED", "").lower() == "true"
        )

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        # 健康检查端点始终放行，便于负载均衡探测
        if path in ("/api/v1/health", "/api/v1/"):
            return await call_next(request)

        # 允许 CORS 预检请求通过，浏览器不会在 OPTIONS 请求中携带自定义头
        if request.method == "OPTIONS":
            return await call_next(request)

        # 未配置 API Key 且未显式允许未认证访问时，默认拒绝所有非健康检查请求
        if not self.api_key and not self.allow_unauthenticated:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: API key not configured"},
            )

        if not self.api_key:
            return await call_next(request)

        # 安全加固：仅接受 X-API-Key 请求头，不接受 URL 查询参数方式传递 API Key
        # 原因：查询参数会出现在服务器日志、浏览器历史中，增加泄露风险
        provided = request.headers.get("X-API-Key")
        # 使用时序安全比较，防止基于响应时间的 API Key 长度/内容探测攻击
        if provided is None or not hmac.compare_digest(provided, self.api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: invalid or missing API key"},
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    基于内存的滑动窗口限流中间件。

    默认每分钟每个 IP 最多 60 次请求；求解端点（/api/v1/solve）限制为
    每分钟 10 次，降低计算资源被滥用的风险。
    额外限制内存中保存的 IP 条目总数，防止海量伪造 IP 导致内存无限增长。
    """

    def __init__(
        self,
        app,
        default_limit: int = 60,
        window_seconds: int = 60,
        path_limits: dict[str, int] | None = None,
        disabled: bool | None = None,
        max_ips: int | None = None,
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.path_limits = path_limits or {"/api/v1/solve": 10, "/api/v1/solve/async": 10}
        # 使用普通 dict 而非 defaultdict，便于在条目清空后彻底删除键
        self._requests: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()
        # disabled 为 None 时从环境变量读取，便于测试显式注入独立配置
        self._disabled = (
            disabled
            if disabled is not None
            else os.getenv("GREENVRP_RATE_LIMIT_DISABLED", "").lower() == "true"
        )
        self.max_ips = (
            max_ips
            if max_ips is not None
            else int(os.getenv("GREENVRP_RATE_LIMIT_MAX_IPS", "10000"))
        )

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """获取客户端真实 IP。

        优先从受信任代理头 X-Forwarded-For 获取最左侧 IP，
        不存在时回退到直接连接地址。生产环境应配合受信任代理列表使用。
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For 格式：client, proxy1, proxy2，取最左侧真实客户端 IP
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _purge_expired_ips(self, now: float) -> None:
        """清理窗口期内完全没有请求或全部时间戳已过期的 IP 条目。"""
        expired = [
            ip for ip, ts in self._requests.items() if not ts or now - ts[-1] >= self.window_seconds
        ]
        for ip in expired:
            del self._requests[ip]

    async def dispatch(self, request: Request, call_next: Callable):
        # 通过环境变量可整体禁用限流（仅用于基准测试等场景）
        if self._disabled:
            return await call_next(request)

        # CORS 预检请求不消耗限流配额
        if request.method == "OPTIONS":
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        path = request.url.path
        limit = self.path_limits.get(path, self.default_limit)
        now = time.time()

        async with self._lock:
            # 清理当前 IP 的过期时间戳
            window = self._requests.get(client_ip)
            if window is not None:
                window[:] = [t for t in window if now - t < self.window_seconds]
                if not window:
                    del self._requests[client_ip]
                    window = None

            # 接近或达到 IP 上限时，触发全量过期清理
            if len(self._requests) >= self.max_ips:
                self._purge_expired_ips(now)

            # 新 IP 且清理后仍无空位，则拒绝请求
            if window is None and len(self._requests) >= self.max_ips:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests, please try again later"},
                )

            window = self._requests.setdefault(client_ip, [])
            if len(window) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests, please try again later"},
                )

            window.append(now)

        return await call_next(request)
