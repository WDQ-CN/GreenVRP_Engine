"""
单元测试：core/solver.py
"""

import pandas as pd
import pytest

from core.solver import (
    GreenVRPSolver,
    solve_with_multiple_strategies,
    solve_with_multiple_strategies_parallel,
)
from tests.fixtures.customers import (
    get_invalid_customers_df,
    get_test_customers_df,
    get_test_vehicle_config,
)


class TestGreenVRPSolverInit:
    def test_valid_init(self):
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, vehicle_config=get_test_vehicle_config())
        assert solver.num_vehicles == 5  # 3 + 2
        assert len(solver.locations) == len(df)

    def test_missing_columns_raises(self):
        df = pd.DataFrame({"id": [0, 1], "lat": [39.9, 39.91]})
        with pytest.raises(ValueError, match="缺少必要列"):
            GreenVRPSolver(df)

    def test_empty_data_raises(self):
        df = pd.DataFrame(
            columns=[
                "id",
                "name",
                "lat",
                "lon",
                "demand",
                "service_time_min",
                "tw_earliest",
                "tw_latest",
            ]
        )
        with pytest.raises(ValueError, match="客户数据不能为空"):
            GreenVRPSolver(df)

    def test_invalid_time_window_raises(self):
        df = get_invalid_customers_df()
        with pytest.raises(ValueError, match="时间窗无效"):
            GreenVRPSolver(df)


class TestGreenVRPSolverSolve:
    def test_solve_success(self):
        df = get_test_customers_df()
        solver = GreenVRPSolver(
            df,
            vehicle_config=get_test_vehicle_config(),
            search_time_limit=5,
        )
        result = solver.solve()
        assert result["solution_status"] == "SUCCESS"
        assert "routes" in result
        assert "total_distance" in result
        assert "solve_time_seconds" in result
        assert result["solve_time_seconds"] >= 0

    def test_vehicles_used_not_empty(self):
        df = get_test_customers_df()
        solver = GreenVRPSolver(
            df,
            vehicle_config=get_test_vehicle_config(),
            search_time_limit=5,
        )
        result = solver.solve()
        assert sum(result["vehicles_used"].values()) > 0

    def test_solve_with_params(self):
        df = get_test_customers_df()
        solver = GreenVRPSolver(
            df,
            vehicle_config=get_test_vehicle_config(),
            search_time_limit=5,
        )
        result = solver.solve_with_params()
        assert result["solution_status"] == "SUCCESS"


class TestSolveWithMultipleStrategies:
    def test_multiple_strategies(self):
        df = get_test_customers_df()
        result = solve_with_multiple_strategies(
            customers_df=df,
            vehicle_config=get_test_vehicle_config(),
            time_limit=5,
        )
        assert result["solution_status"] == "SUCCESS"
        assert "total_distance" in result


class TestSolveWithMultipleStrategiesParallel:
    def test_parallel_strategies(self):
        df = get_test_customers_df()
        result = solve_with_multiple_strategies_parallel(
            customers_df=df,
            vehicle_config=get_test_vehicle_config(),
            time_limit=5,
            max_workers=2,
        )
        assert result["solution_status"] == "SUCCESS"
        assert "solve_time_seconds" in result
