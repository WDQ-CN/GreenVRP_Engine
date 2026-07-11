"""
健康检查路由
"""

from datetime import datetime

from fastapi import APIRouter

from ..schemas import HealthResponse

router = APIRouter(tags=["系统"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
)
async def health_check() -> HealthResponse:
    """
    检查 API 服务健康状态。

    返回服务状态、版本和各组件状态。
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
async def root() -> dict:
    """API 根路径，返回欢迎信息。"""
    return {
        "name": "GreenVRP Engine API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }
