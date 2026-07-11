"""
求解器路由

提供同步/异步求解端点。
使用依赖注入获取 SolverService，支持测试时替换为 Mock。
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from core.interfaces import ISolverService
from exceptions.errors import GreenVRPError, JobNotFoundError

from ..dependencies import get_solver_service
from ..schemas import JobStatusResponse, SolveRequest, SolveResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/solve", tags=["求解器"])
jobs_router = APIRouter(prefix="/jobs", tags=["任务管理"])


def _build_solver_payload(request: SolveRequest) -> dict[str, Any]:
    """将 Pydantic 请求转换为 solver_service 所需字典格式。"""
    customers = [c.model_dump() for c in request.customers]
    vehicle_config = None
    if request.vehicle_config:
        vehicle_config = {k: v.model_dump() for k, v in request.vehicle_config.items()}
    params = request.params.model_dump() if request.params else None
    return {
        "customers": customers,
        "vehicle_config": vehicle_config,
        "params": params,
    }


@router.post(
    "",
    response_model=SolveResponse,
    summary="同步求解",
    description="提交求解请求并等待结果返回",
)
async def solve_sync(
    request: SolveRequest,
    solver: ISolverService = Depends(get_solver_service),
) -> SolveResponse:
    """
    同步求解 VRPTW 问题。

    - **customers**: 客户数据列表（必须包含仓库）
    - **vehicle_config**: 可选，车型配置
    - **params**: 可选，求解参数
    """
    customer_count = len(request.customers)
    logger.info("接收到同步求解请求: customers=%d", customer_count)
    payload = _build_solver_payload(request)
    try:
        # 执行求解
        result = solver.solve_sync(**payload)

        logger.info(
            "同步求解请求完成: customers=%d, solve_time=%.2fs",
            customer_count,
            result.get("solve_time_seconds", 0),
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

    except GreenVRPError:
        logger.warning("同步求解业务异常: customers=%d", customer_count)
        # 业务异常由全局异常处理器统一处理，不泄露内部细节
        raise
    except Exception:
        logger.exception("同步求解失败: customers=%d", customer_count)
        raise HTTPException(
            status_code=500,
            detail="求解失败，请稍后重试或联系管理员",
        ) from None


@router.post(
    "/async",
    response_model=dict[str, Any],
    summary="异步求解",
    description="提交异步求解任务，立即返回任务ID",
)
async def solve_async(
    request: SolveRequest,
    solver: ISolverService = Depends(get_solver_service),
) -> dict[str, Any]:
    """
    异步求解 VRPTW 问题。

    立即返回任务ID，可通过 /jobs/{job_id} 查询状态。
    """
    customer_count = len(request.customers)
    logger.info(
        "接收到异步求解请求: customers=%d, callback=%s",
        customer_count,
        request.callback_url or "无",
    )
    payload = _build_solver_payload(request)
    try:
        # 创建异步任务（后台执行，不阻塞事件循环）
        job_id = await solver.solve_async(
            **payload,
            callback_url=request.callback_url,
        )

        logger.info(
            "异步任务已创建: job_id=%s, customers=%d",
            job_id,
            customer_count,
        )

        return {
            "job_id": job_id,
            "status": "pending",
            "message": "任务已创建，请通过 /api/v1/jobs/{job_id} 查询状态",
        }

    except GreenVRPError:
        logger.warning("异步任务创建业务异常: customers=%d", customer_count)
        # 业务异常由全局异常处理器统一处理
        raise
    except Exception:
        logger.exception("异步任务创建失败: customers=%d", customer_count)
        raise HTTPException(
            status_code=500,
            detail="任务创建失败，请稍后重试或联系管理员",
        ) from None


@jobs_router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="查询任务状态",
)
async def get_job_status(
    job_id: str,
    solver: ISolverService = Depends(get_solver_service),
) -> JobStatusResponse:
    """
    查询异步求解任务的状态。

    - **job_id**: 任务ID
    """
    logger.debug("查询任务状态: job_id=%s", job_id)
    job = solver.get_job_status(job_id)

    if not job:
        logger.warning("任务不存在: job_id=%s", job_id)
        raise JobNotFoundError(job_id)

    logger.debug("任务状态查询结果: job_id=%s, status=%s", job_id, job["status"])
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        created_at=job["created_at"],
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        message=job.get("error_message"),
    )


@jobs_router.get(
    "/{job_id}/result",
    response_model=SolveResponse,
    summary="获取任务结果",
)
async def get_job_result(
    job_id: str,
    solver: ISolverService = Depends(get_solver_service),
) -> SolveResponse:
    """
    获取已完成任务的求解结果。

    - **job_id**: 任务ID
    """
    logger.debug("获取任务结果: job_id=%s", job_id)
    job = solver.get_job_status(job_id)

    if not job:
        logger.warning("任务结果查询失败: job_id=%s 不存在", job_id)
        raise JobNotFoundError(job_id)

    if job["status"] != "completed":
        logger.warning(
            "任务结果查询失败: job_id=%s 状态=%s（需 completed）",
            job_id,
            job["status"],
        )
        raise HTTPException(
            status_code=400,
            detail=f"任务未完成，当前状态: {job['status']}",
        )

    logger.info(
        "任务结果返回: job_id=%s, status=%s",
        job_id,
        job["status"],
    )
    return SolveResponse(
        job_id=job_id,
        status="completed",
        solution=job["solution"],
        cost_result=job["cost_result"],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
    )
