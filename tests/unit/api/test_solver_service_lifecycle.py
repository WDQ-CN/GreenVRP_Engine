"""SolverService 生命周期与后台任务管理回归测试。"""

import asyncio
import contextlib

import pytest

from api.services.solver_service import SolverService
from exceptions.errors import ServiceUnavailableError


def _run(coro):
    """在同步测试函数中运行异步协程的辅助函数。"""
    return asyncio.run(coro)


@pytest.fixture
def service():
    """创建用于生命周期测试的 SolverService 实例。"""
    return SolverService(max_background_tasks=2, shutdown_timeout=0.1)


def test_background_task_limit_rejects(service, monkeypatch):
    """后台任务数达到上限后，新的 solve_async 应被拒绝。"""

    async def slow_execute(*args, **kwargs):
        await asyncio.sleep(60)

    monkeypatch.setattr(service, "_execute_job", slow_execute)

    async def _inner():
        await service.solve_async([])
        await service.solve_async([])
        with pytest.raises(ServiceUnavailableError):
            await service.solve_async([])

    _run(_inner())


def test_close_waits_for_tasks(service, monkeypatch):
    """close() 应等待运行中的后台任务完成。"""
    executed = False

    async def fast_execute(*args, **kwargs):
        nonlocal executed
        await asyncio.sleep(0.01)
        executed = True

    monkeypatch.setattr(service, "_execute_job", fast_execute)

    async def _inner():
        await service.solve_async([])
        await service.close()
        assert executed

    _run(_inner())


def test_close_cancels_after_timeout(service, monkeypatch):
    """close() 超时后应取消未完成的后台任务。"""

    async def slow_execute(*args, **kwargs):
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.sleep(60)

    monkeypatch.setattr(service, "_execute_job", slow_execute)

    async def _inner():
        await service.solve_async([])
        await service.close(timeout=0.05)
        assert len(service._background_tasks) == 0

    _run(_inner())


def test_shutdown_rejects_new_tasks(service):
    """设置 shutdown 事件后，solve_async 应拒绝新任务。"""

    async def _inner():
        service._shutdown_event.set()
        with pytest.raises(ServiceUnavailableError):
            await service.solve_async([])

    _run(_inner())
