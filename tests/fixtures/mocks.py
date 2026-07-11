"""
Mock 对象工厂

提供项目中关键外部依赖的 Mock 实现：
- MockSolver: 模拟 OR-Tools 求解器输出
- MockSolverService: 模拟 API 服务层
- MockJobManager: 模拟任务管理器
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock


def make_mock_solution(
    total_distance: float = 100.0,
    total_cost: float = 500.0,
    carbon_emission_kg: float = 25.0,
    num_routes: int = 2,
    route_distance: float = 50.0,
    status: str = "SUCCESS",
) -> Dict[str, Any]:
    """生成模拟的求解器返回结果（结构同 core/solver.py 的 _extract_solution 输出）。"""
    routes = []
    for i in range(num_routes):
        routes.append(
            {
                "vehicle_id": i,
                "vehicle_type": "4.2m",
                "vehicle_color": "#1f77b4",
                "capacity": 800,
                "stops": [
                    {
                        "node": 0,
                        "customer_id": 0,
                        "customer_name": "仓库",
                        "lat": 39.9042,
                        "lon": 116.4074,
                        "demand": 0,
                        "arrival_time": 480,
                        "service_time": 0,
                        "tw_earliest": 480,
                        "tw_latest": 960,
                        "late_minutes": 0,
                        "is_late": False,
                    },
                    {
                        "node": i + 1,
                        "customer_id": i + 1,
                        "customer_name": f"客户{chr(65 + i)}",
                        "lat": 39.9123 + i * 0.01,
                        "lon": 116.3456 + i * 0.01,
                        "demand": 45,
                        "arrival_time": 520 + i * 10,
                        "service_time": 15,
                        "tw_earliest": 500,
                        "tw_latest": 600 + i * 20,
                        "late_minutes": 0,
                        "is_late": False,
                    },
                ],
                "distance_km": route_distance,
                "total_demand": 45,
                "total_time_min": 15 + i * 5,
                "late_minutes": 0,
            }
        )

    return {
        "solution": {
            "routes": routes,
            "total_distance": total_distance,
            "vehicles_used": {"4.2m": num_routes, "7.6m": 0},
            "total_late_minutes": 0,
            "solution_status": status,
        },
        "cost_result": {
            "total_cost": total_cost,
            "transport_cost": total_cost * 0.4,
            "fixed_cost": total_cost * 0.2,
            "labor_cost": total_cost * 0.25,
            "carbon_cost": total_cost * 0.1,
            "penalty_cost": total_cost * 0.05,
            "carbon_emission_kg": carbon_emission_kg,
            "total_distance_km": total_distance,
            "total_time_min": 120,
            "total_late_minutes": 0,
            "cost_breakdown": {
                "transport_cost": total_cost * 0.4,
                "fixed_cost": total_cost * 0.2,
                "labor_cost": total_cost * 0.25,
                "carbon_cost": total_cost * 0.1,
                "penalty_cost": total_cost * 0.05,
            },
        },
    }


def make_mock_job(
    job_id: str = "test-job-001",
    status: str = "pending",
    with_result: bool = False,
) -> Dict[str, Any]:
    """生成模拟的任务状态字典。"""
    now = datetime.now(timezone.utc)
    job: Dict[str, Any] = {
        "job_id": job_id,
        "status": status,
        "created_at": now.isoformat(),
        "started_at": None,
        "completed_at": None,
        "solution": None,
        "cost_result": None,
        "error_message": None,
    }

    if status in ("running", "completed", "failed"):
        job["started_at"] = now.isoformat()

    if status == "completed" and with_result:
        result = make_mock_solution()
        job["solution"] = result["solution"]
        job["cost_result"] = result["cost_result"]
        job["completed_at"] = now.isoformat()

    if status == "failed":
        job["error_message"] = "求解器内部错误"
        job["completed_at"] = now.isoformat()

    return job


class MockSolver:
    """模拟 OR-Tools 求解器。

    用于测试 core/solver.py 时替代真实的 pywrapcp 调用。
    """

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.solve_called = False
        self.last_params = None

    def solve(self, customers_df=None, vehicle_config=None, params=None) -> Dict[str, Any]:
        """模拟 solve() 调用。"""
        self.solve_called = True
        self.last_params = params

        if self.should_fail:
            raise RuntimeError("Mock solver failure")

        return make_mock_solution()

    def __call__(self, *args, **kwargs):
        return self.solve(*args, **kwargs)


class MockSolverService:
    """模拟 SolverService。

    用于测试 API 路由时替代真实的 solver_service 模块。
    """

    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self._solver = MockSolver()

    def solve_sync(
        self,
        customers: List[Dict[str, Any]],
        vehicle_config: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """模拟同步求解。"""
        return make_mock_solution()

    def solve_async(
        self,
        customers: List[Dict[str, Any]],
        vehicle_config: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None,
    ) -> str:
        """模拟异步求解，创建任务并返回 ID。"""
        job_id = f"async-job-{len(self.jobs) + 1:03d}"
        self.jobs[job_id] = make_mock_job(job_id, status="running")
        return job_id

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """模拟任务状态查询。"""
        job = self.jobs.get(job_id)
        if job is None:
            return None
        # 首次查询后标记为 completed（模拟任务完成）
        if job["status"] == "running":
            self.jobs[job_id] = make_mock_job(job_id, status="completed", with_result=True)
        return self.jobs[job_id]

    def reset(self):
        """重置状态。"""
        self.jobs.clear()


class MockJobManager:
    """模拟 JobManager。

    用于测试 api/services/redis_job_manager.py 时替代 Redis 后端。
    """

    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self._closed = False

    def create_job(self, job_id: str) -> bool:
        if self._closed:
            return False
        self.jobs[job_id] = make_mock_job(job_id)
        return True

    def update_job(self, job_id: str, data: Dict[str, Any]) -> bool:
        if self._closed or job_id not in self.jobs:
            return False
        self.jobs[job_id].update(data)
        return True

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

    def close(self):
        self._closed = True


class MockRedis:
    """模拟 Redis 客户端。

    用于测试依赖 Redis 的代码路径。
    """

    def __init__(self):
        self._data: Dict[str, str] = {}

    def get(self, key: str) -> Optional[str]:
        return self._data.get(key)

    def set(self, key: str, value: str, **kwargs) -> bool:
        self._data[key] = value
        return True

    def delete(self, key: str) -> int:
        return 1 if self._data.pop(key, None) is not None else 0

    def exists(self, key: str) -> int:
        return 1 if key in self._data else 0

    def pipeline(self):
        return MagicMock()
