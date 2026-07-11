"""
求解器服务层

封装核心求解逻辑，供 API 调用。
"""

import asyncio
import hashlib
import ipaddress
import json
import logging
import os
import re
import socket
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx
import pandas as pd

from config.constants import DEFAULT_PARAMS
from config.vehicles import DEFAULT_VEHICLE_CONFIG
from core import (
    GreenVRPSolver,
    calculate_green_cost,
    solve_with_multiple_strategies,
)
from core.interfaces import IJobManager, ISolverService
from core.solver import solve_with_multiple_strategies_parallel
from exceptions.errors import GreenVRPError, ServiceUnavailableError, ValidationError

logger = logging.getLogger(__name__)


class JobManager:
    """任务管理器（内存版，生产环境应使用 Redis）。"""

    def __init__(self):
        self._jobs: dict[str, dict[str, Any]] = {}

    def create_job(self) -> str:
        """创建新任务，返回任务ID。"""
        job_id = str(uuid.uuid4())  # 使用完整UUID避免碰撞
        self._jobs[job_id] = {
            "status": "pending",
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "solution": None,
            "cost_result": None,
            "error_message": None,
        }
        self._prune_jobs()
        return job_id

    def update_job(self, job_id: str, **kwargs) -> None:
        """更新任务状态。"""
        if job_id in self._jobs:
            self._jobs[job_id].update(kwargs)

    def get_job(self, job_id: str) -> None | dict[str, Any]:
        """获取任务信息。"""
        return self._jobs.get(job_id)

    def _prune_jobs(self, max_size: int = 1000) -> None:
        """简单的LRU风格 pruning：保留最近 max_size 条任务记录。"""
        if len(self._jobs) <= max_size:
            return
        # 按 created_at 排序，移除最旧的
        sorted_jobs = sorted(self._jobs.items(), key=lambda kv: kv[1]["created_at"])
        for key, _ in sorted_jobs[: len(self._jobs) - max_size]:
            self._jobs.pop(key, None)

    def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        """列出所有任务。"""
        jobs = list(self._jobs.values())
        return jobs[:limit]


# 内网与危险协议黑名单，用于 callback_url SSRF 校验
_CALLBACK_BLOCKED_SCHEMES = {"file", "ftp", "gopher", "dict", "ldap", "tftp"}
_CALLBACK_PRIVATE_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


def _validate_callback_url(url: str | None) -> None:
    """
    校验回调 URL，防止 SSRF。

    限制条件：
    - 仅允许 http / https 协议
    - 禁止 IP 地址与内网地址
    - 禁止 localhost 及常见私有网段
    """
    if url is None:
        return

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme in _CALLBACK_BLOCKED_SCHEMES or scheme not in {"http", "https"}:
        raise ValidationError(
            f"callback_url 协议不支持: {scheme}",
            field="callback_url",
            value=url,
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValidationError(
            "callback_url 缺少主机名",
            field="callback_url",
            value=url,
        )

    # 禁止裸 IP
    try:
        ip = ipaddress.ip_address(hostname)
        raise ValidationError(
            "callback_url 不允许使用 IP 地址",
            field="callback_url",
            value=url,
        )
    except ValueError:
        pass

    # 禁止 localhost 与常见内网域名模式
    lower_host = hostname.lower()
    if lower_host in {"localhost", "localhost.localdomain"}:
        raise ValidationError(
            "callback_url 不允许指向 localhost",
            field="callback_url",
            value=url,
        )
    if re.search(r"\.(local|internal|corp|home|lan)$", lower_host):
        raise ValidationError(
            "callback_url 不允许指向私有域名后缀",
            field="callback_url",
            value=url,
        )

    # DNS 解析后再次检查是否指向私有 IP（添加超时防止阻塞）
    try:
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(5.0)  # DNS 解析超时 5 秒
        try:
            resolved = socket.getaddrinfo(hostname, None)
        finally:
            socket.setdefaulttimeout(original_timeout)

        for _, _, _, _, sockaddr in resolved:
            ip = ipaddress.ip_address(sockaddr[0])
            if any(ip in network for network in _CALLBACK_PRIVATE_NETWORKS):
                raise ValidationError(
                    "callback_url 解析后指向私有网络地址",
                    field="callback_url",
                    value=url,
                )
    except socket.gaierror as exc:
        raise ValidationError(
            "callback_url 主机名无法解析",
            field="callback_url",
            value=url,
        ) from exc
    except OSError as _exc:
        # 包含 DNS 解析超时在内的操作系统级网络错误
        raise ValidationError(
            "callback_url DNS 解析超时",
            field="callback_url",
            value=url,
        ) from _exc


class SolverService(ISolverService):
    """求解器服务类。

    实现 ISolverService 接口，支持 JobManager 依赖注入。
    可通过构造函数传入不同的 JobManager 实现（内存版/Redis版）。
    """

    def __init__(
        self,
        job_manager: IJobManager | None = None,
        max_background_tasks: int | None = None,
        shutdown_timeout: float = 30.0,
    ):
        """
        初始化求解器服务。

        Args:
            job_manager: 任务管理器实例，默认为内存版 JobManager
            max_background_tasks: 最大并发后台任务数，默认从环境变量读取
            shutdown_timeout: 优雅关闭时等待后台任务的最大秒数
        """
        self.job_manager = job_manager or JobManager()
        # 求解结果内存缓存：对相同客户/车型/参数的重复请求直接返回缓存，
        # 显著降低重试、对比等场景的响应时间。
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_lock = threading.RLock()
        self._cache_max_size = 128
        self._cache_ttl_seconds = 300
        # 保存后台任务强引用，防止任务被垃圾回收导致 "Task was destroyed but it is pending!"
        # 同时避免未处理的异常被静默吞掉。
        self._background_tasks: set[asyncio.Task] = set()
        self._bg_task_lock = asyncio.Lock()
        self._max_background_tasks = max_background_tasks or int(
            os.getenv("GREENVRP_MAX_BACKGROUND_TASKS", "10")
        )
        self._shutdown_timeout = shutdown_timeout
        self._shutdown_event = asyncio.Event()
        logger.info(
            "SolverService 初始化: job_manager=%s, max_background_tasks=%d",
            type(self.job_manager).__name__,
            self._max_background_tasks,
        )

    def _solve_cache_key(
        self,
        customers: list[dict[str, Any]],
        vehicle_config: None | dict[str, Any],
        params: None | dict[str, Any],
    ) -> str:
        """生成求解结果缓存键（基于客户、车型、参数的确定性哈希）。"""
        # 按 id 排序并固定字段顺序，确保相同输入得到相同键
        customer_keys = [
            "id",
            "lat",
            "lon",
            "demand",
            "service_time_min",
            "tw_earliest",
            "tw_latest",
        ]
        normalized_customers = sorted(
            ([{k: c[k] for k in customer_keys if k in c} for c in customers]),
            key=lambda x: x["id"],
        )
        cache_payload = {
            "customers": normalized_customers,
            "vehicle_config": vehicle_config,
            "params": params,
        }
        return hashlib.md5(
            json.dumps(cache_payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()

    def _serialize_result(self, result: dict[str, Any]) -> bytes | dict[str, Any]:
        """将求解结果序列化为 bytes；遇到不可序列化类型时回退到 deepcopy。"""
        try:
            return json.dumps(result, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        except TypeError:
            logger.warning("求解结果包含不可序列化类型，回退到 deepcopy 缓存")
            return deepcopy(result)

    @staticmethod
    def _deserialize_result(payload: bytes | dict[str, Any]) -> dict[str, Any]:
        """反序列化缓存中的求解结果；若存储的是原始对象则深拷贝返回。"""
        if isinstance(payload, bytes):
            return json.loads(payload)
        return deepcopy(payload)

    def _get_cached_result(self, key: str) -> dict[str, Any] | None:
        """线程安全地读取缓存，同时进行 TTL 与 LRU 清理。"""
        now = time.time()
        with self._cache_lock:
            # 先清理过期条目
            expired = [k for k, v in self._cache.items() if now - v["ts"] > self._cache_ttl_seconds]
            for k in expired:
                del self._cache[k]
            entry = self._cache.get(key)
            if entry is None:
                return None
            entry["ts"] = now  # 更新最近访问时间
            entry["hits"] = entry.get("hits", 0) + 1
            return self._deserialize_result(entry["result"])

    def _set_cached_result(self, key: str, result: dict[str, Any]) -> None:
        """线程安全地写入缓存，超出容量时淘汰最久未访问条目。"""
        now = time.time()
        with self._cache_lock:
            # 容量控制：淘汰最旧条目
            while len(self._cache) >= self._cache_max_size:
                oldest = min(self._cache, key=lambda k: self._cache[k]["ts"])
                del self._cache[oldest]
            self._cache[key] = {
                "ts": now,
                "hits": 0,
                "result": self._serialize_result(result),
            }

    def solve_sync(
        self,
        customers: list[dict[str, Any]],
        vehicle_config: None | dict[str, Any] = None,
        params: None | dict[str, Any] = None,
    ) -> dict[str, Any]:
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
        customer_count = len(customers)

        # 转换为 DataFrame
        customers_df = pd.DataFrame(customers)

        # 使用默认配置
        config = vehicle_config or DEFAULT_VEHICLE_CONFIG
        solver_params = {**DEFAULT_PARAMS, **(params or {})}

        # 尝试命中求解结果缓存
        cache_key = self._solve_cache_key(customers, config, solver_params)
        cached = self._get_cached_result(cache_key)
        if cached is not None:
            logger.info(
                "同步求解命中缓存: customers=%d, cache_key=%s",
                customer_count,
                cache_key,
            )
            return cached

        time_limit = solver_params.get("search_time_limit", 30)
        use_multi_strategy = solver_params.get("use_multi_strategy", True)
        use_parallel = solver_params.get("use_parallel", True)

        logger.info(
            "同步求解开始: customers=%d, time_limit=%ds, multi_strategy=%s, parallel=%s",
            customer_count,
            time_limit,
            use_multi_strategy,
            use_parallel,
        )

        # 求解
        if use_multi_strategy and use_parallel:
            try:
                solution = solve_with_multiple_strategies_parallel(
                    customers_df=customers_df,
                    vehicle_config=config,
                    time_penalty_per_min=solver_params.get("late_penalty_per_min", 10.0),
                    time_limit=time_limit,
                )
            except Exception:
                logger.warning(
                    "并行求解失败，回退到串行模式: customers=%d",
                    customer_count,
                )
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
        route_count = len(solution.get("routes", []))
        logger.info(
            "同步求解完成: route_count=%d, total_distance=%.2f, solve_time=%.2fs",
            route_count,
            solution.get("total_distance", 0),
            solve_time,
        )

        result = {
            "solution": solution,
            "cost_result": cost_result,
            "solve_time_seconds": solve_time,
        }
        self._set_cached_result(cache_key, result)
        return result

    async def solve_async(
        self,
        customers: list[dict[str, Any]],
        vehicle_config: None | dict[str, Any] = None,
        params: None | dict[str, Any] = None,
        callback_url: None | str = None,
    ) -> str:
        """
        异步求解（创建任务后在后台执行）。

        Args:
            customers: 客户数据列表
            vehicle_config: 车型配置
            params: 求解参数
            callback_url: 完成回调URL

        Returns:
            任务ID
        """
        _validate_callback_url(callback_url)

        if self._shutdown_event.is_set():
            raise ServiceUnavailableError("SolverService 正在关闭，不再接受新的异步任务")

        async with self._bg_task_lock:
            if len(self._background_tasks) >= self._max_background_tasks:
                raise ServiceUnavailableError(
                    f"后台求解任务数已达上限 {self._max_background_tasks}，请稍后再试"
                )

            job_id = self.job_manager.create_job()
            logger.info(
                "异步任务创建: job_id=%s, customers=%d, callback=%s",
                job_id,
                len(customers),
                callback_url or "无",
            )

            # 在后台线程池中执行求解，不阻塞 API 事件循环。
            # 使用 asyncio.create_task 替代已弃用的 ensure_future，并保存引用避免被 GC。
            task = asyncio.create_task(
                self._execute_job(job_id, customers, vehicle_config, params, callback_url)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        return job_id

    async def _execute_job(
        self,
        job_id: str,
        customers: list[dict[str, Any]],
        vehicle_config: None | dict[str, Any] = None,
        params: None | dict[str, Any] = None,
        callback_url: None | str = None,
    ) -> None:
        """
        在后台执行求解任务并更新状态。

        使用 asyncio.to_thread 将同步求解调用放入线程池，
        避免阻塞主事件循环。
        """
        try:
            logger.info("异步任务开始执行: job_id=%s", job_id)
            self.job_manager.update_job(
                job_id,
                status="processing",
                started_at=datetime.now(),
            )

            # 在独立线程中执行同步求解，避免阻塞事件循环
            result = await asyncio.to_thread(self.solve_sync, customers, vehicle_config, params)

            self.job_manager.update_job(
                job_id,
                status="completed",
                completed_at=datetime.now(),
                solution=result["solution"],
                cost_result=result["cost_result"],
            )

            logger.info(
                "异步任务 %s 完成，耗时 %.2f 秒", job_id, result.get("solve_time_seconds", 0)
            )

            # 回调通知（如果有）
            if callback_url:
                await self._send_callback(callback_url, job_id, "completed")

        except asyncio.CancelledError:
            logger.warning("异步任务被取消: job_id=%s", job_id)
            self.job_manager.update_job(
                job_id,
                status="failed",
                completed_at=datetime.now(),
                error_message="任务因服务关闭被取消",
            )
            if callback_url:
                await self._send_callback(
                    callback_url, job_id, "failed", error="任务因服务关闭被取消"
                )
            raise

        except GreenVRPError as exc:
            logger.warning(
                "异步任务业务异常: job_id=%s, error=%s",
                job_id,
                exc,
            )
            self.job_manager.update_job(
                job_id,
                status="failed",
                completed_at=datetime.now(),
                error_message=str(exc),
            )
            if callback_url:
                await self._send_callback(callback_url, job_id, "failed", error=str(exc))

        except Exception:
            logger.exception("异步任务 %s 执行失败", job_id)
            self.job_manager.update_job(
                job_id,
                status="failed",
                completed_at=datetime.now(),
                error_message="内部错误",
            )
            if callback_url:
                await self._send_callback(callback_url, job_id, "failed", error="内部错误")

    async def _send_callback(
        self,
        url: str,
        job_id: str,
        status: str,
        error: None | str = None,
    ) -> None:
        """
        发送异步回调通知。

        使用 httpx 发送 HTTP POST 请求通知调用方任务完成状态。

        Args:
            url: 回调 URL
            job_id: 任务 ID
            status: 任务状态 (completed/failed)
            error: 错误信息（可选）
        """
        try:
            payload = {
                "job_id": job_id,
                "status": status,
            }
            if error:
                payload["error"] = error

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info("回调通知已发送: job=%s, status=%s, url=%s", job_id, status, url)
        except Exception as exc:
            logger.warning("回调通知发送失败: job=%s, url=%s, error=%s", job_id, url, exc)

    async def close(self, timeout: float | None = None) -> None:
        """优雅关闭 SolverService。

        设置关闭标志，阻止新任务创建；等待已有后台任务完成，超时后取消剩余任务。
        注意：由于 `asyncio.to_thread` 中的同步求解线程无法被强制终止，`close()`
        只能在 `to_thread` 返回后的下一个 await 点触发取消。
        """
        timeout = timeout or self._shutdown_timeout
        self._shutdown_event.set()

        async with self._bg_task_lock:
            pending = list(self._background_tasks)

        if not pending:
            logger.info("SolverService 关闭：无运行中后台任务")
            return

        logger.info(
            "SolverService 关闭中，等待 %d 个后台任务，超时 %.1fs",
            len(pending),
            timeout,
        )
        try:
            await asyncio.wait_for(
                asyncio.gather(*pending, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("后台任务等待超时，取消未完成任务")
            async with self._bg_task_lock:
                for task in list(self._background_tasks):
                    if not task.done():
                        task.cancel()
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        logger.info("SolverService 已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """异步上下文管理器退出时自动关闭。"""
        await self.close()

    def get_job_status(self, job_id: str) -> None | dict[str, Any]:
        """获取任务状态。"""
        job = self.job_manager.get_job(job_id)
        if job is None:
            logger.warning("任务不存在: job_id=%s", job_id)
        else:
            logger.debug("查询任务状态: job_id=%s, status=%s", job_id, job.get("status"))
        return job
