"""
求解器服务层

封装核心求解逻辑，供 API 调用。
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd

from config.constants import DEFAULT_PARAMS
from config.security import security_config
from config.vehicles import DEFAULT_VEHICLE_CONFIG
from core import (
    GreenVRPSolver,
    calculate_green_cost,
    solve_with_multiple_strategies,
)
from core.solver import solve_with_multiple_strategies_parallel
from .redis_job_manager import create_job_manager


# 全局任务管理器（生产环境使用 Redis，开发环境降级到内存）
job_manager = create_job_manager(use_fallback=True)


class SolverService:
    """求解器服务类。"""

    def __init__(self):
        self.job_manager = job_manager

    def solve_sync(
        self,
        customers: List[Dict[str, Any]],
        vehicle_config: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        同步求解。

        Args:
            customers: 客户数据列表
            vehicle_config: 车型配置
            params: 求解参数

        Returns:
            包含 solution 和 cost_result 的字典
        """
        start_time = time.time()

        # 转换为 DataFrame
        customers_df = pd.DataFrame(customers)

        # 使用默认配置
        config = vehicle_config or DEFAULT_VEHICLE_CONFIG
        solver_params = {**DEFAULT_PARAMS, **(params or {})}

        # 提取求解参数
        time_limit = solver_params.get("search_time_limit", 30)
        use_multi_strategy = solver_params.get("use_multi_strategy", True)
        use_parallel = solver_params.get("use_parallel", True)

        # 求解
        if use_multi_strategy and use_parallel:
            try:
                solution = solve_with_multiple_strategies_parallel(
                    customers_df=customers_df,
                    vehicle_config=config,
                    time_penalty_per_min=solver_params.get("late_penalty_per_min", 10.0),
                    time_limit=time_limit,
                )
            except Exception as e:
                # 回退到串行模式
                solution = solve_with_multiple_strategies(
                    customers_df=customers_df,
                    vehicle_config=config,
                    time_penalty_per_min=solver_params.get("late_penalty_per_min", 10.0),
                    time_limit=time_limit,
                )
        elif use_multi_strategy:
            solution = solve_with_multiple_strategies(
                customers_df=customers_df,
                vehicle_config=config,
                time_penalty_per_min=solver_params.get("late_penalty_per_min", 10.0),
                time_limit=time_limit,
            )
        else:
            solver = GreenVRPSolver(
                customers_df=customers_df,
                vehicle_config=config,
                time_penalty_per_min=solver_params.get("late_penalty_per_min", 10.0),
                search_time_limit=time_limit,
            )
            solution = solver.solve()

        # 计算成本
        cost_result = calculate_green_cost(solution, config, solver_params)

        solve_time = time.time() - start_time

        return {
            "solution": solution,
            "cost_result": cost_result,
            "solve_time_seconds": solve_time,
        }

    async def solve_async(
        self,
        customers: List[Dict[str, Any]],
        vehicle_config: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None,
    ) -> str:
        """
        异步求解（创建任务）。
        
        使用 asyncio.to_thread() 将 CPU 密集型求解任务放到线程池执行，
        避免阻塞事件循环。

        Args:
            customers: 客户数据列表
            vehicle_config: 车型配置
            params: 求解参数
            callback_url: 完成回调 URL（已验证安全）

        Returns:
            任务 ID
        """
        job_id = self.job_manager.create_job()

        # 存储回调 URL（已经过验证）
        if callback_url:
            self.job_manager.update_job(job_id, callback_url=callback_url)

        # 使用 asyncio.to_thread() 将同步求解任务放到线程池执行
        # 这样不会阻塞事件循环，允许并发处理其他请求
        async def run_job():
            try:
                self.job_manager.update_job(
                    job_id,
                    status="processing",
                    started_at=datetime.now(),
                )

                # 在线程池中执行 CPU 密集型的同步求解
                result = await asyncio.to_thread(
                    self.solve_sync, customers, vehicle_config, params
                )

                self.job_manager.update_job(
                    job_id,
                    status="completed",
                    completed_at=datetime.now(),
                    solution=result["solution"],
                    cost_result=result["cost_result"],
                )

                # 回调通知（如果有）
                if callback_url:
                    await self._send_callback(callback_url, job_id, "completed")

            except Exception as e:
                self.job_manager.update_job(
                    job_id,
                    status="failed",
                    completed_at=datetime.now(),
                    error_message=str(e),
                )

                if callback_url:
                    await self._send_callback(callback_url, job_id, "failed", str(e))

        # 启动后台任务
        asyncio.create_task(run_job())

        return job_id

    async def _send_callback(
        self,
        url: str,
        job_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        """
        发送回调通知（安全实现）。

        Args:
            url: 回调 URL（已验证）
            job_id: 任务 ID
            status: 任务状态
            error: 错误消息（可选）
        """
        # 再次验证 URL 安全性（防御性编程）
        is_valid, error_msg = security_config.validate_callback_url(url)
        if not is_valid:
            print(f"回调 URL 验证失败：{error_msg}")
            return

        payload = {
            "job_id": job_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }

        if error:
            payload["error"] = error

        try:
            # 使用 httpx 发送异步请求，设置超时
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                print(f"回调成功：{url}, 状态码：{response.status_code}")
        except httpx.TimeoutException:
            print(f"回调超时：{url}")
        except httpx.RequestError as e:
            print(f"回调请求失败：{url}, 错误：{str(e)}")
        except Exception as e:
            print(f"回调异常：{url}, 错误：{str(e)}")

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态。"""
        return self.job_manager.get_job(job_id)


# 全局服务实例
solver_service = SolverService()
