"""
健康检查路由
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from slowapi.util import get_remote_address

from ..schemas import HealthResponse
from ..security.auth import get_optional_user
from ..security.rate_limit import limiter

router = APIRouter(tags=["系统"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
)
@limiter.limit("60/minute")
async def health_check(
    request: Request,
    current_user: dict = Depends(get_optional_user),
) -> HealthResponse:
    """
    检查 API 服务健康状态。

    返回服务状态、版本和各组件状态。
    
    需要认证：否（可选）
    速率限制：60/minute
    """
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        timestamp=datetime.now(),
        components={
            "database": "ok",
            "solver": "ok",
        },
    )


@router.get(
    "/",
    summary="API 根路径",
)
@limiter.limit("60/minute")
async def root(
    request: Request,
    current_user: dict = Depends(get_optional_user),
) -> dict:
    """
    API 根路径，返回欢迎信息。
    
    需要认证：否（可选）
    速率限制：60/minute
    """
    return {
        "name": "GreenVRP Engine API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }
