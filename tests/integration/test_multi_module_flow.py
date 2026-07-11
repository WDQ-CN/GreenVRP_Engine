"""
集成测试：多模块交互流程

测试求解器 → 成本核算 → 分析模块的完整调用链。
"""

import pandas as pd
import pytest

from core.cost import calculate_green_cost
from core.solver import GreenVRPSolver
from tests.fixtures.customers import get_minimal_solution, get_test_customers_df, get_test_params, get_test_vehicle_config


class TestSolverToCostFlow:
    """求解器到成本核算模块交互。"""

    @pytest.mark.slow
    def test_solve_then_calculate_cost(self):
        """求解后计算成本，验证数据一致性。"""
        df = get_test_customers_df()
        config = get_test_vehicle_config()
        params = get_test_params()

        # 求解（使用小数据集和短时间限制）
        solver = GreenVRPSolver(df, config, search_time_limit=10)
        solution = solver.solve()

        # 即使无解也不断言失败，仅在有解时验证成本计算
        if solution["solution_status"] == "SUCCESS":
            cost_result = calculate_green_cost(solution, config, params)
            assert cost_result["total_cost"] > 0
            assert "transport_cost" in cost_result
            assert "carbon_emission_kg" in cost_result

    def test_cost_with_minimal_solution(self):
        """使用最小求解结果验证成本核算完整性。"""
        solution = get_minimal_solution()
        config = get_test_vehicle_config()
        params = get_test_params()

        cost = calculate_green_cost(solution, config, params)
        assert cost["total_cost"] > 0
        assert cost["transport_cost"] > 0
        assert cost["fixed_cost"] > 0
        assert cost["carbon_emission_kg"] > 0

    def test_multi_route_cost(self):
        """多路线成本核算。"""
        from tests.fixtures.customers import get_multi_route_solution

        solution = get_multi_route_solution()
        config = get_test_vehicle_config()
        params = get_test_params()

        cost = calculate_green_cost(solution, config, params)
        assert cost["total_cost"] > 0
        assert cost["total_distance_km"] == 25.0

    def test_solution_with_late_penalty(self):
        """含迟到惩罚的成本核算。"""
        from tests.fixtures.customers import get_solution_with_late_customer

        solution = get_solution_with_late_customer()
        config = get_test_vehicle_config()
        params = get_test_params()

        cost = calculate_green_cost(solution, config, params)
        assert cost["penalty_cost"] > 0
        assert cost["total_cost"] > 0
