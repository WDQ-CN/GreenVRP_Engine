"""
速率限制模块

使用 slowapi 实现基于 IP 和 API Key 的速率限制。
支持自定义密钥函数、分级限流和优雅的错误处理。
"""

import logging
from typing import Optional

from fastapi import Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config.security import security_config

# 配置日志
logger = logging.getLogger(__name__)


def get_rate_limit_key(request: Request) -> str:
    """
    获取速率限制的键值。
    
    优先使用 API Key 作为键值，其次使用 IP 地址。
    这样可以避免同一 API Key 在不同 IP 间共享限额。
    """
    # 尝试从请求头获取 API Key
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key.strip():
        return f"apikey:{api_key.strip()}"
    
    # 退回到 IP 地址
    return f"ip:{get_remote_address(request)}"


# 创建速率限制器
limiter = Limiter(key_func=get_rate_limit_key)


async def rate_limit_exceeded_handler(
    request: Request, 
    exc: RateLimitExceeded
) -> Response:
    """
    自定义速率限制超出处理器。
    
    记录日志并返回友好的错误信息。
    """
    logger.warning(
        f"Rate limit exceeded for {get_rate_limit_key(request)} "
        f"on path {request.url.path}"
    )
    
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={
            "error": "请求频率过高",
            "detail": "请稍后再试",
            "retry_after": exc.detail.split(":")[-1].strip() if ":" in exc.detail else "60"
        },
        headers={"Retry-After": "60"}
    )


def setup_rate_limiting(app):
    """
    在 FastAPI 应用上设置速率限制。

    Args:
        app: FastAPI 应用实例
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# 常用速率限制策略
RATE_LIMIT_DEFAULT: str = security_config.RATE_LIMIT_DEFAULT
RATE_LIMIT_SOLVER: str = security_config.RATE_LIMIT_SOLVER
RATE_LIMIT_UPLOAD: str = security_config.RATE_LIMIT_UPLOAD
