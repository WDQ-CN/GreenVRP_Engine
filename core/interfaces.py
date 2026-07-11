"""
核心接口模块

使用 Protocol 定义模块间交互契约，降低耦合度。
实现类无需显式继承，满足接口即可。

设计原则：
- 使用 Protocol（结构化类型）而非 ABC，降低侵入性
- 每个接口职责单一，方法签名清晰
- 为新实现（RedisJobManager、MockSolverService）提供契约
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ISolverService(Protocol):
    """求解器服务接口。

    定义求解器服务的公共契约，支持同步/异步求解和任务状态查询。
    """

    def solve_sync(
        self,
        customers: list[dict[str, Any]],
        vehicle_config: dict[str, dict[str, Any]] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """同步求解 VRPTW 问题。"""
        ...

    async def solve_async(
        self,
        customers: list[dict[str, Any]],
        vehicle_config: dict[str, dict[str, Any]] | None = None,
        params: dict[str, Any] | None = None,
        callback_url: str | None = None,
    ) -> str:
        """异步求解（创建任务后在后台执行）。"""
        ...

    def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """获取任务状态。"""
        ...


@runtime_checkable
class IJobManager(Protocol):
    """任务管理器接口。

    管理异步求解任务的生命周期，支持内存和 Redis 等不同实现。
    """

    def create_job(self) -> str:
        """创建新任务，返回任务ID。"""
        ...

    def update_job(self, job_id: str, **kwargs: Any) -> None:
        """更新任务状态。"""
        ...

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """获取任务信息。"""
        ...

    def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        """列出所有任务。"""
        ...
