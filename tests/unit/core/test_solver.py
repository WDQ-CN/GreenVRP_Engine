"""
单元测试：core/solver.py — SolverInstancePool, CallbackCache 和核心求解方法
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from core.solver import CallbackCache, GreenVRPSolver, SolverInstancePool
from exceptions.errors import SolverError
from tests.fixtures.customers import (
    get_invalid_customers_df,
    get_test_customers_df,
    get_test_vehicle_config,
)


class TestSolverInstancePool:
    def test_init(self):
        pool = SolverInstancePool(max_size=5)
        assert pool.max_size == 5
        assert len(pool._pool) == 0

    def test_get_or_create(self):
        pool = SolverInstancePool(max_size=5)
        with patch("core.solver.pywrapcp.RoutingIndexManager") as mock_mgr, \
             patch("core.solver.pywrapcp.RoutingModel") as mock_model:
            mock_mgr.return_value = "manager"
            mock_model.return_value = "routing"
            r1 = pool.get_or_create("k1", 10, 3)
            r2 = pool.get_or_create("k1", 10, 3)
            assert r1 == r2  # 内容相同
            # 验证只创建了一次
            assert mock_mgr.call_count == 1

    def test_eviction(self):
        pool = SolverInstancePool(max_size=2)
        with patch("core.solver.pywrapcp.RoutingIndexManager") as mock_mgr, \
             patch("core.solver.pywrapcp.RoutingModel") as mock_model:
            mock_mgr.return_value = "mgr"
            mock_model.return_value = "routing"
            pool.get_or_create("k1", 10, 3)
            pool.get_or_create("k2", 10, 3)
            pool.get_or_create("k3", 10, 3)
            assert len(pool._pool) == 2
            assert "k1" not in pool._pool

    def test_clear(self):
        pool = SolverInstancePool(max_size=5)
        with patch("core.solver.pywrapcp.RoutingIndexManager") as mock_mgr, \
             patch("core.solver.pywrapcp.RoutingModel") as mock_model:
            mock_mgr.return_value = "mgr"
            mock_model.return_value = "routing"
            pool.get_or_create("k1", 10, 3)
            pool.clear()
            assert len(pool._pool) == 0


class TestCallbackCache:
    def test_get_or_create(self):
        cache = CallbackCache()
        fn = lambda: "result"
        r1 = cache.get_or_create("t1", fn)
        r2 = cache.get_or_create("t1", fn)
        assert r1 is r2

    def test_clear(self):
        cache = CallbackCache()
        cache.get_or_create("t1", lambda: 1)
        cache.clear()
        assert len(cache._cache) == 0


class TestGreenVRPSolverInit:
    """GreenVRPSolver 初始化和数据验证测试。"""

    def test_init_with_valid_data(self):
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())
        assert solver.num_vehicles == 5
        assert solver.time_penalty_per_min == 10.0
        assert solver.search_time_limit == 30

    def test_init_with_minimal_vehicle_config(self):
        df = get_test_customers_df()
        config = {
            "4.2m": {"capacity": 800, "fixed_cost": 200, "fuel_per_100km": 12, "speed_kmh": 40, "count": 2, "color": "#1f77b4"}
        }
        solver = GreenVRPSolver(df, config)
        assert solver.num_vehicles == 2

    def test_validate_data_raises_error_for_missing_columns(self):
        df = pd.DataFrame({"id": [1], "lat": [39.9]})
        with pytest.raises(SolverError, match="缺少必要列"):
            GreenVRPSolver(df, get_test_vehicle_config())

    def test_validate_data_raises_error_for_empty_dataframe(self):
        df = pd.DataFrame(columns=["id", "name", "lat", "lon", "demand", "service_time_min", "tw_earliest", "tw_latest"])
        with pytest.raises(SolverError, match="不能为空"):
            GreenVRPSolver(df, get_test_vehicle_config())

    def test_validate_data_raises_error_for_invalid_time_windows(self):
        df = get_invalid_customers_df()
        with pytest.raises(SolverError, match="时间窗无效"):
            GreenVRPSolver(df, get_test_vehicle_config())


class TestGreenVRPSolverUtility:
    """工具方法测试。"""

    def test_create_empty_result(self):
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())
        result = solver._create_empty_result("NO_SOLUTION_FOUND")
        assert result["solution_status"] == "NO_SOLUTION_FOUND"
        assert result["routes"] == []
        assert result["total_distance"] == 0
        assert result["vehicles_used"] == {"4.2m": 0, "7.6m": 0}
        assert result["total_late_minutes"] == 0

    def test_generate_cache_key(self):
        df = get_test_customers_df()
        solver1 = GreenVRPSolver(df, get_test_vehicle_config())
        solver2 = GreenVRPSolver(df, get_test_vehicle_config())
        assert solver1._cache_key == solver2._cache_key

    def test_generate_cache_key_different_params(self):
        df = get_test_customers_df()
        solver1 = GreenVRPSolver(df, get_test_vehicle_config(), time_penalty_per_min=5.0)
        solver2 = GreenVRPSolver(df, get_test_vehicle_config(), time_penalty_per_min=10.0)
        assert solver1._cache_key != solver2._cache_key

    def test_build_vehicle_list(self):
        """验证异构车队构建正确。"""
        df = get_test_customers_df()
        config = get_test_vehicle_config()
        solver = GreenVRPSolver(df, config)
        assert len(solver.vehicles) == 5
        assert solver.vehicles[0]["type"] == "4.2m"
        assert solver.vehicles[3]["type"] == "7.6m"
        assert solver.vehicle_type_map[0] == "4.2m"

    def test_build_locations(self):
        """验证位置列表和距离矩阵构建。"""
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())
        assert len(solver.locations) == 6
        assert len(solver.demands) == 6
        assert len(solver.distance_matrix) == 6


class TestGreenVRPSolverSolve:
    """solve() 方法测试（mock OR-Tools）。"""

    @patch("core.solver.pywrapcp.RoutingModel")
    @patch("core.solver.pywrapcp.RoutingIndexManager")
    def test_solve_produces_valid_result_structure(self, mock_mgr, mock_model):
        """验证 solve() 返回结果包含所有必要字段。"""
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())

        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        mock_mgr.return_value = MagicMock()
        mock_instance.RegisterTransitCallback.return_value = 0
        mock_instance.RegisterUnaryTransitCallback.return_value = 1
        mock_instance.GetDimensionOrDie.return_value = MagicMock()

        mock_solution = MagicMock()
        mock_instance.SolveWithParameters.return_value = mock_solution

        with patch.object(solver, '_extract_solution') as mock_extract:
            mock_extract.return_value = {
                "routes": [
                    {
                        "vehicle_id": 0, "vehicle_type": "4.2m", "vehicle_color": "#1f77b4",
                        "capacity": 800, "stops": [], "distance_km": 0,
                        "total_demand": 0, "total_time_min": 0, "late_minutes": 0,
                    }
                ],
                "total_distance": 0,
                "vehicles_used": {"4.2m": 1, "7.6m": 0},
                "total_late_minutes": 0,
                "solution_status": "SUCCESS",
            }
            result = solver.solve()

            assert "routes" in result
            assert "total_distance" in result
            assert "vehicles_used" in result
            assert "total_late_minutes" in result
            assert "solution_status" in result
            assert "solve_time_seconds" in result
            assert result["solution_status"] == "SUCCESS"

    @patch("core.solver.pywrapcp.RoutingModel")
    @patch("core.solver.pywrapcp.RoutingIndexManager")
    def test_solve_no_solution_found(self, mock_mgr, mock_model):
        """当 OR-Tools 返回无解时的处理。"""
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())

        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        mock_mgr.return_value = MagicMock()
        mock_instance.RegisterTransitCallback.return_value = 0
        mock_instance.RegisterUnaryTransitCallback.return_value = 1
        mock_instance.GetDimensionOrDie.return_value = MagicMock()

        mock_instance.SolveWithParameters.return_value = None

        result = solver.solve()
        assert result["solution_status"] == "NO_SOLUTION_FOUND"
        assert result["routes"] == []
        assert result["total_distance"] == 0

    @patch("core.solver.pywrapcp.RoutingModel")
    @patch("core.solver.pywrapcp.RoutingIndexManager")
    def test_solve_runs_full_pipeline(self, mock_mgr, mock_model):
        """验证 solve() 完整调用链。"""
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())

        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        mock_mgr.return_value = MagicMock()
        mock_instance.RegisterTransitCallback.return_value = 0
        mock_instance.RegisterUnaryTransitCallback.return_value = 1
        mock_instance.GetDimensionOrDie.return_value = MagicMock()

        mock_solution = MagicMock()
        mock_instance.SolveWithParameters.return_value = mock_solution

        with patch.object(solver, '_extract_solution') as mock_extract:
            mock_extract.return_value = {
                "routes": [], "total_distance": 0,
                "vehicles_used": {"4.2m": 0, "7.6m": 0},
                "total_late_minutes": 0, "solution_status": "SUCCESS",
            }
            result = solver.solve()

            # 验证调用了关键 OR-Tools 方法
            assert mock_instance.SetArcCostEvaluatorOfAllVehicles.called
            assert mock_instance.AddDimensionWithVehicleCapacity.called
            assert mock_instance.AddDimensionWithVehicleTransits.called
            assert mock_instance.SolveWithParameters.called

    @patch("core.solver.pywrapcp.RoutingModel")
    @patch("core.solver.pywrapcp.RoutingIndexManager")
    def test_solve_with_solution_has_depot_stop(self, mock_mgr, mock_model):
        """验证有解返回时 solve() 正确调用 _extract_solution。"""
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())

        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        mock_mgr.return_value = MagicMock()
        mock_instance.RegisterTransitCallback.return_value = 0
        mock_instance.RegisterUnaryTransitCallback.return_value = 1
        mock_instance.GetDimensionOrDie.return_value = MagicMock()

        mock_solution = MagicMock()
        mock_instance.SolveWithParameters.return_value = mock_solution

        with patch.object(solver, '_extract_solution') as mock_extract:
            mock_extract.return_value = {
                "routes": [
                    {
                        "vehicle_id": 0, "vehicle_type": "4.2m", "vehicle_color": "#1f77b4",
                        "capacity": 800, "stops": [
                            {"node": 0, "customer_id": 0, "customer_name": "仓库", "lat": 39.9, "lon": 116.4, "demand": 0},
                            {"node": 1, "customer_id": 1, "customer_name": "客户A", "lat": 39.91, "lon": 116.34, "demand": 45},
                            {"node": 0, "customer_id": None, "customer_name": "仓库", "lat": 39.9, "lon": 116.4, "demand": 0},
                        ], "distance_km": 10.0,
                        "total_demand": 45, "total_time_min": 30, "late_minutes": 0,
                    }
                ],
                "total_distance": 10.0,
                "vehicles_used": {"4.2m": 1, "7.6m": 0},
                "total_late_minutes": 0,
                "solution_status": "SUCCESS",
            }
            result = solver.solve()
            assert result["solution_status"] == "SUCCESS"
            assert len(result["routes"][0]["stops"]) == 3


class TestGreenVRPSolverSolveWithParams:
    """solve_with_params() 方法测试。"""

    @patch("core.solver.pywrapcp.RoutingModel")
    @patch("core.solver.pywrapcp.RoutingIndexManager")
    def test_solve_with_params_default(self, mock_mgr, mock_model):
        """验证默认参数调用。"""
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())

        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        mock_mgr.return_value = MagicMock()
        mock_instance.RegisterTransitCallback.return_value = 0
        mock_instance.RegisterUnaryTransitCallback.return_value = 1
        mock_instance.GetDimensionOrDie.return_value = MagicMock()

        mock_solution = MagicMock()
        mock_instance.SolveWithParameters.return_value = mock_solution

        with patch.object(solver, '_extract_solution') as mock_extract:
            mock_extract.return_value = {
                "routes": [], "total_distance": 0,
                "vehicles_used": {"4.2m": 0, "7.6m": 0},
                "total_late_minutes": 0, "solution_status": "SUCCESS",
            }
            result = solver.solve_with_params()
            assert result["solution_status"] == "SUCCESS"

    @patch("core.solver.pywrapcp.RoutingModel")
    @patch("core.solver.pywrapcp.RoutingIndexManager")
    def test_solve_with_params_custom_time_limit(self, mock_mgr, mock_model):
        """验证自定义时间限制生效。"""
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())

        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        mock_mgr.return_value = MagicMock()
        mock_instance.RegisterTransitCallback.return_value = 0
        mock_instance.RegisterUnaryTransitCallback.return_value = 1
        mock_instance.GetDimensionOrDie.return_value = MagicMock()

        mock_solution = MagicMock()
        mock_instance.SolveWithParameters.return_value = mock_solution

        with patch.object(solver, '_extract_solution') as mock_extract:
            mock_extract.return_value = {
                "routes": [], "total_distance": 0,
                "vehicles_used": {"4.2m": 0, "7.6m": 0},
                "total_late_minutes": 0, "solution_status": "SUCCESS",
            }
            result = solver.solve_with_params(time_limit=120)
            assert result["solution_status"] == "SUCCESS"

    @patch("core.solver.pywrapcp.RoutingModel")
    @patch("core.solver.pywrapcp.RoutingIndexManager")
    def test_solve_with_params_no_solution(self, mock_mgr, mock_model):
        """无解时的处理。"""
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())

        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        mock_mgr.return_value = MagicMock()
        mock_instance.RegisterTransitCallback.return_value = 0
        mock_instance.RegisterUnaryTransitCallback.return_value = 1
        mock_instance.GetDimensionOrDie.return_value = MagicMock()

        mock_instance.SolveWithParameters.return_value = None

        result = solver.solve_with_params()
        assert result["solution_status"] == "NO_SOLUTION_FOUND"


class TestGreenVRPSolverAdaptiveSearchParams:
    """自适应搜索参数测试。"""

    def test_small_problem(self):
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())
        params = solver._get_adaptive_search_params(6)
        assert params.time_limit.seconds <= 15

    def test_large_problem(self):
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())
        params = solver._get_adaptive_search_params(100)
        assert params.time_limit.seconds >= 30

    def test_difficulty_factor(self):
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())
        params = solver._get_adaptive_search_params(30, problem_difficulty=2.0)
        assert params.time_limit.seconds >= 60

    def test_xlarge_problem(self):
        df = get_test_customers_df()
        solver = GreenVRPSolver(df, get_test_vehicle_config())
        params = solver._get_adaptive_search_params(300)
        assert params.time_limit.seconds >= 120


class TestDefaultStrategies:
    """测试默认求解策略配置（方案二：扩展策略）。"""

    def test_strategies_count(self):
        """默认策略应为 5 种（从3种扩展而来）。"""
        from core.solver import _get_default_strategies
        strategies = _get_default_strategies()
        assert len(strategies) == 5

    def test_strategies_format(self):
        """每种策略应包含 (initial_solution, metaheuristic) 二元组。"""
        from core.solver import _get_default_strategies
        strategies = _get_default_strategies()
        for strategy in strategies:
            assert len(strategy) == 2
            assert isinstance(strategy[0], int)
            assert isinstance(strategy[1], int)

    def test_strategies_unique(self):
        """策略组合应各不相同。"""
        from core.solver import _get_default_strategies
        strategies = _get_default_strategies()
        strategy_set = set(strategies)
        assert len(strategy_set) == len(strategies)


class TestSelectBestSolution:
    """测试最优解选择逻辑。"""

    def test_select_best_by_distance(self):
        """选择总距离最短的解（车辆数相同的情况下）。"""
        from core.solver import _select_best_solution
        solutions = [
            {"solution_status": "SUCCESS", "total_distance": 100,
             "total_late_minutes": 0, "vehicles_used": {"a": 1}},
            {"solution_status": "SUCCESS", "total_distance": 80,
             "total_late_minutes": 0, "vehicles_used": {"a": 1}},
            {"solution_status": "SUCCESS", "total_distance": 120,
             "total_late_minutes": 0, "vehicles_used": {"a": 1}},
        ]
        best = _select_best_solution(solutions)
        assert best["total_distance"] == 80

    def test_select_best_with_late_penalty(self):
        """迟到时间影响选择（每迟到1分钟=0.5km惩罚）。"""
        from core.solver import _select_best_solution
        solutions = [
            {"solution_status": "SUCCESS", "total_distance": 100,
             "total_late_minutes": 0, "vehicles_used": {"a": 1}},
            {"solution_status": "SUCCESS", "total_distance": 90,
             "total_late_minutes": 100, "vehicles_used": {"a": 1}},
        ]
        best = _select_best_solution(solutions)
        assert best["total_distance"] == 100  # 无迟到的优先（100 < 90+50=140）

    def test_select_best_fewer_vehicles(self):
        """车辆数影响选择（每辆车=5km惩罚）。"""
        from core.solver import _select_best_solution
        solutions = [
            {"solution_status": "SUCCESS", "total_distance": 100,
             "total_late_minutes": 0, "vehicles_used": {"a": 2}},
            {"solution_status": "SUCCESS", "total_distance": 105,
             "total_late_minutes": 0, "vehicles_used": {"a": 1}},
        ]
        best = _select_best_solution(solutions)
        # Score1: 100 + 0 + 2*5 = 110, Score2: 105 + 0 + 1*5 = 110
        # Tie, first found wins (distance=100)
        assert best["total_distance"] == 100

    def test_no_solutions(self):
        """空列表返回 None。"""
        from core.solver import _select_best_solution
        assert _select_best_solution([]) is None

    def test_all_failed(self):
        """全部失败返回 None。"""
        from core.solver import _select_best_solution
        solutions = [
            {"solution_status": "ERROR", "total_distance": 100},
            {"solution_status": "NO_SOLUTION_FOUND", "total_distance": 80},
        ]
        assert _select_best_solution(solutions) is None


class TestSolveWithMultipleStrategiesIntegration:
    """测试多策略求解和后处理集成（方案二+四）。"""

    def test_solve_returns_success(self):
        """小规模数据应能成功求解。"""
        df = get_test_customers_df()
        config = get_test_vehicle_config()
        from core.solver import solve_with_multiple_strategies
        result = solve_with_multiple_strategies(
            customers_df=df,
            vehicle_config=config,
            time_limit=15,
        )
        assert result["solution_status"] == "SUCCESS"
        assert result["total_distance"] > 0
        assert len(result["routes"]) > 0

    def test_vehicles_used_is_dict(self):
        """vehicles_used 应为字典。"""
        df = get_test_customers_df()
        config = get_test_vehicle_config()
        from core.solver import solve_with_multiple_strategies
        result = solve_with_multiple_strategies(
            customers_df=df,
            vehicle_config=config,
            time_limit=15,
        )
        assert isinstance(result["vehicles_used"], dict)
        for v_type in config:
            assert v_type in result["vehicles_used"]

    def test_routes_have_required_fields(self):
        """路线应包含必要字段。"""
        df = get_test_customers_df()
        config = get_test_vehicle_config()
        from core.solver import solve_with_multiple_strategies
        result = solve_with_multiple_strategies(
            customers_df=df,
            vehicle_config=config,
            time_limit=15,
        )
        for route in result["routes"]:
            assert "stops" in route
            assert "vehicle_type" in route
            assert route["distance_km"] >= 0
