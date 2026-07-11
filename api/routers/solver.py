"""
求解器路由

提供同步/异步求解端点。
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request

from ..schemas import JobStatusResponse, SolveRequest, SolveResponse
from ..security.auth import get_current_user
from ..security.rate_limit import RATE_LIMIT_SOLVER, limiter
from ..services import solver_service
from config.security import security_config

router = APIRouter(prefix="/solve", tags=["求解器"])


@router.post(
    "",
    response_model=SolveResponse,
    summary="同步求解",
    description="提交求解请求并等待结果返回",
)
@limiter.limit(RATE_LIMIT_SOLVER)
async def solve_sync(
    request: Request,
    body: SolveRequest,
    current_user: dict = Depends(get_current_user),
) -> SolveResponse:
    """
    同步求解 VRPTW 问题。

    - **customers**: 客户数据列表（必须包含仓库）
    - **vehicle_config**: 可选，车型配置
    - **params**: 可选，求解参数
    
    需要认证：是（API Key 或 JWT Token）
    速率限制：{RATE_LIMIT_SOLVER}
    """
    try:
        # 转换请求格式
        customers = [c.model_dump() for c in body.customers]
        vehicle_config = None
        if body.vehicle_config:
            vehicle_config = {k: v.model_dump() for k, v in body.vehicle_config.items()}
        params = body.params.model_dump() if body.params else None

        # 验证 callback_url 安全性
        if body.callback_url:
            is_valid, error_msg = security_config.validate_callback_url(body.callback_url)
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"回调 URL 不安全：{error_msg}",
                )

        # 执行求解
        result = solver_service.solve_sync(
            customers=customers,
            vehicle_config=vehicle_config,
            params=params,
        )

        # 构建响应
        return SolveResponse(
            job_id="sync",
            status="completed",
            solution=result["solution"],
            cost_result=result["cost_result"],
            created_at=datetime.now(),
            completed_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"求解失败：{str(e)}")


@router.post(
    "/async",
    response_model=Dict[str, Any],
    summary="异步求解",
    description="提交异步求解任务，立即返回任务 ID",
)
@limiter.limit(RATE_LIMIT_SOLVER)
async def solve_async(
    request: Request,
    body: SolveRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    异步求解 VRPTW 问题。

    立即返回任务 ID，可通过 /jobs/{job_id} 查询状态。
    
    需要认证：是（API Key 或 JWT Token）
    速率限制：{RATE_LIMIT_SOLVER}
    """
    try:
        # 转换请求格式
        customers = [c.model_dump() for c in body.customers]
        vehicle_config = None
        if body.vehicle_config:
            vehicle_config = {k: v.model_dump() for k, v in body.vehicle_config.items()}
        params = body.params.model_dump() if body.params else None

        # 验证 callback_url 安全性
        if body.callback_url:
            is_valid, error_msg = security_config.validate_callback_url(body.callback_url)
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"回调 URL 不安全：{error_msg}",
                )

        # 创建异步任务
        job_id = await solver_service.solve_async(
            customers=customers,
            vehicle_config=vehicle_config,
            params=params,
            callback_url=body.callback_url,
        )

        return {
            "job_id": job_id,
            "status": "pending",
            "message": "任务已创建，请通过 /api/v1/jobs/{job_id} 查询状态",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"任务创建失败：{str(e)}")


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="查询任务状态",
)
@limiter.limit("100/minute")
async def get_job_status(
    request: Request,
    job_id: str,
    current_user: dict = Depends(get_current_user),
) -> JobStatusResponse:
    """
    查询异步求解任务的状态。

    - **job_id**: 任务 ID
    
    需要认证：是（API Key 或 JWT Token）
    """
    job = solver_service.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"任务不存在：{job_id}")

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        created_at=job["created_at"],
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        message=job.get("error_message"),
    )


@router.get(
    "/jobs/{job_id}/result",
    response_model=SolveResponse,
    summary="获取任务结果",
)
@limiter.limit("100/minute")
async def get_job_result(
    request: Request,
    job_id: str,
    current_user: dict = Depends(get_current_user),
) -> SolveResponse:
    """
    获取已完成任务的求解结果。

    - **job_id**: 任务 ID
    
    需要认证：是（API Key 或 JWT Token）
    """
    job = solver_service.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"任务不存在：{job_id}")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"任务未完成，当前状态：{job['status']}",
        )

    return SolveResponse(
        job_id=job_id,
        status="completed",
        solution=job["solution"],
        cost_result=job["cost_result"],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
    )
