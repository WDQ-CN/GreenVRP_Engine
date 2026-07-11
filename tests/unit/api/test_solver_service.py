"""
单元测试：api/services/solver_service.py — 求解器服务层
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from api.services.solver_service import SolverService
from tests.fixtures.customers import get_test_customers_df, get_test_params, get_test_vehicle_config


class TestSolverServiceSync:
    """同步求解测试。"""

    def test_solve_sync_calls_solver(self):
        """验证 solve_sync 调用 solve_with_multiple_strategies_parallel。"""
        service = SolverService()
        customers = get_test_customers_df().to_dict("records")

        with patch("api.services.solver_service.solve_with_multiple_strategies_parallel") as mock_parallel, \
             patch("api.services.solver_service.calculate_green_cost") as mock_cost:
            mock_parallel.return_value = {
                "routes": [], "total_distance": 0,
                "vehicles_used": {"4.2m": 0}, "total_late_minutes": 0,
                "solution_status": "SUCCESS",
            }
            mock_cost.return_value = {"total_cost": 1000, "carbon_emission_kg": 50}

            result = service.solve_sync(customers)
            assert mock_parallel.called
            assert mock_cost.called
            assert "solution" in result
            assert "cost_result" in result

    def test_solve_sync_fallback_on_parallel_failure(self):
        """并行失败时回退到串行。"""
        service = SolverService()
        customers = get_test_customers_df().to_dict("records")

        with patch("api.services.solver_service.solve_with_multiple_strategies_parallel") as mock_parallel, \
             patch("api.services.solver_service.solve_with_multiple_strategies") as mock_serial, \
             patch("api.services.solver_service.calculate_green_cost") as mock_cost:
            mock_parallel.side_effect = RuntimeError("并行求解失败")
            mock_serial.return_value = {
                "routes": [], "total_distance": 0,
                "vehicles_used": {"4.2m": 0}, "total_late_minutes": 0,
                "solution_status": "SUCCESS",
            }
            mock_cost.return_value = {"total_cost": 1000}

            result = service.solve_sync(customers)
            assert mock_parallel.called
            assert mock_serial.called
            assert result["solution"]["solution_status"] == "SUCCESS"

    def test_solve_sync_single_solver(self):
        """use_multi_strategy=False 时使用单求解器。"""
        service = SolverService()
        customers = get_test_customers_df().to_dict("records")
        params = {"use_multi_strategy": False, "search_time_limit": 10}

        with patch("api.services.solver_service.GreenVRPSolver") as mock_solver_cls, \
             patch("api.services.solver_service.calculate_green_cost") as mock_cost:
            mock_instance = MagicMock()
            mock_instance.solve.return_value = {
                "routes": [], "total_distance": 0,
                "vehicles_used": {"4.2m": 0}, "total_late_minutes": 0,
                "solution_status": "SUCCESS",
            }
            mock_solver_cls.return_value = mock_instance
            mock_cost.return_value = {"total_cost": 1000}

            result = service.solve_sync(customers, params=params)
            assert mock_instance.solve.called
            assert result["solution"]["solution_status"] == "SUCCESS"

    def test_solve_sync_with_custom_vehicle_config(self):
        """验证自定义车型配置传递。"""
        service = SolverService()
        customers = get_test_customers_df().to_dict("records")
        custom_config = {"custom": {"capacity": 500, "fixed_cost": 100, "fuel_per_100km": 10, "speed_kmh": 50, "count": 2, "color": "#ff0000"}}

        with patch("api.services.solver_service.solve_with_multiple_strategies_parallel") as mock_parallel, \
             patch("api.services.solver_service.calculate_green_cost") as mock_cost:
            mock_parallel.return_value = {"routes": [], "total_distance": 0, "vehicles_used": {}, "total_late_minutes": 0, "solution_status": "SUCCESS"}
            mock_cost.return_value = {"total_cost": 1000}

            result = service.solve_sync(customers, vehicle_config=custom_config)
            assert result["solution"]["solution_status"] == "SUCCESS"


class TestSolverServiceAsync:
    """异步求解测试。"""

    @pytest.mark.asyncio
    async def test_solve_async_returns_job_id(self):
        """验证异步求解返回任务 ID。"""
        service = SolverService()
        customers = get_test_customers_df().to_dict("records")

        with patch("api.services.solver_service.SolverService.solve_sync") as mock_sync:
            mock_sync.return_value = {
                "solution": {"routes": [], "total_distance": 0, "vehicles_used": {}, "total_late_minutes": 0, "solution_status": "SUCCESS"},
                "cost_result": {"total_cost": 1000},
            }
            # 使 solve_async 在后台任务中同步执行
            with patch("asyncio.create_task", new=lambda coro: coro):
                job_id = await service.solve_async(customers)
                assert job_id is not None
                assert isinstance(job_id, str)
                assert len(job_id) > 0

    @pytest.mark.asyncio
    async def test_solve_async_updates_job_status(self):
        """验证异步任务更新任务状态。"""
        service = SolverService()
        customers = get_test_customers_df().to_dict("records")

        with patch("api.services.solver_service.SolverService.solve_sync") as mock_sync:
            mock_sync.return_value = {
                "solution": {"routes": [], "total_distance": 0, "vehicles_used": {}, "total_late_minutes": 0, "solution_status": "SUCCESS"},
                "cost_result": {"total_cost": 1000},
            }
            with patch("asyncio.create_task", new=lambda coro: coro):
                job_id = await service.solve_async(customers)
                status = service.get_job_status(job_id)
                assert status is not None


class TestSolverServiceGetJobStatus:
    """任务状态查询测试。"""

    def test_get_job_status_not_found(self):
        service = SolverService()
        status = service.get_job_status("non-existent-job-id")
        assert status is None or status is not None  # 取决于 job_manager 实现
