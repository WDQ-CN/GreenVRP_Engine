"""
单元测试：optimization/carbon_aware.py
"""

import pytest

from optimization.carbon_aware import (
    CarbonAwareOptimizer,
    CarbonEfficiencyReport,
)
from tests.fixtures.customers import (
    get_minimal_solution,
    get_test_customers_df,
    get_test_params,
    get_test_vehicle_config,
)


class MockSolverService:
    """符合 ISolverService 接口的伪求解服务。"""

    def solve_sync(self, customers, vehicle_config=None, params=None):
        """返回包含 solution 和 cost_result 的求解结果。"""
        solution = get_minimal_solution()
        cost_result = {
            "transport_cost": 100.0,
            "labor_cost": 50.0,
            "fixed_cost": 200.0,
            "penalty_cost": 0.0,
            "carbon_cost": 20.0,
            "total_cost": 370.0,
            "carbon_emission_kg": 10.0,
            "total_distance_km": 10.0,
            "total_time_min": 60.0,
            "driving_time_min": 45.0,
            "service_time_min": 15.0,
            "waiting_time_min": 0.0,
        }
        return {
            "solution": solution,
            "cost_result": cost_result,
            "solve_time_seconds": 1.0,
        }

    async def solve_async(self, customers, vehicle_config=None, params=None, callback_url=None):
        return "mock-job-id"

    def get_job_status(self, job_id):
        return None


class TestCarbonAwareOptimizer:
    def test_init(self):
        customers = get_test_customers_df().to_dict("records")
        optimizer = CarbonAwareOptimizer(
            MockSolverService(),
            customers,
            get_test_vehicle_config(),
            get_test_params(),
        )
        assert optimizer.solver_service is not None

    def test_optimize_weighted(self):
        customers = get_test_customers_df().to_dict("records")
        optimizer = CarbonAwareOptimizer(
            MockSolverService(),
            customers,
            get_test_vehicle_config(),
            get_test_params(),
        )
        result = optimizer.optimize_for_carbon(method="weighted", time_limit=5)
        assert result["optimization_method"] == "carbon_weighted"
        assert "carbon_target_met" in result

    def test_optimize_constraint_no_target(self):
        customers = get_test_customers_df().to_dict("records")
        optimizer = CarbonAwareOptimizer(
            MockSolverService(),
            customers,
            get_test_vehicle_config(),
            get_test_params(),
        )
        result = optimizer.optimize_for_carbon(method="constraint", time_limit=5)
        # 无目标时回退到 weighted
        assert "carbon_target_met" in result

    def test_optimize_constraint_with_target(self):
        customers = get_test_customers_df().to_dict("records")
        optimizer = CarbonAwareOptimizer(
            MockSolverService(),
            customers,
            get_test_vehicle_config(),
            get_test_params(),
        )
        result = optimizer.optimize_for_carbon(
            carbon_target=1000, method="constraint", time_limit=5
        )
        assert "carbon_target_met" in result

    def test_optimize_hierarchical(self):
        customers = get_test_customers_df().to_dict("records")
        optimizer = CarbonAwareOptimizer(
            MockSolverService(),
            customers,
            get_test_vehicle_config(),
            get_test_params(),
        )
        result = optimizer.optimize_for_carbon(method="hierarchical", time_limit=5)
        assert result["optimization_method"] == "carbon_hierarchical"

    def test_invalid_method_raises(self):
        customers = get_test_customers_df().to_dict("records")
        optimizer = CarbonAwareOptimizer(
            MockSolverService(),
            customers,
            get_test_vehicle_config(),
            get_test_params(),
        )
        with pytest.raises(ValueError, match="未知优化方法"):
            optimizer.optimize_for_carbon(method="unknown")


class TestCarbonEfficiencyReport:
    def test_calculate_carbon_efficiency(self):
        solution = get_minimal_solution()
        customers = get_test_customers_df().to_dict("records")
        optimizer = CarbonAwareOptimizer(
            MockSolverService(),
            customers,
            get_test_vehicle_config(),
            get_test_params(),
        )
        report = optimizer.calculate_carbon_efficiency(solution)
        assert isinstance(report, CarbonEfficiencyReport)
        assert report.total_carbon_kg >= 0
        assert report.carbon_per_km >= 0
        assert len(report.recommendations) > 0

    def test_report_to_dict(self):
        report = CarbonEfficiencyReport(
            total_carbon_kg=100.0,
            carbon_per_km=0.5,
            carbon_per_customer=10.0,
            carbon_per_kg_goods=0.01,
            vehicle_efficiency={"4.2m": 0.02},
            reduction_potential=5.0,
            recommendations=["建议1"],
        )
        d = report.to_dict()
        assert d["total_carbon_kg"] == 100.0
        assert d["recommendations"] == ["建议1"]

    def test_generate_carbon_report(self):
        solution = get_minimal_solution()
        customers = get_test_customers_df().to_dict("records")
        optimizer = CarbonAwareOptimizer(
            MockSolverService(),
            customers,
            get_test_vehicle_config(),
            get_test_params(),
        )
        report_text = optimizer.generate_carbon_report(solution)
        assert "碳排放分析报告" in report_text
        assert "减排建议" in report_text

    def test_compare_carbon_scenarios(self):
        solution = get_minimal_solution()
        customers = get_test_customers_df().to_dict("records")
        optimizer = CarbonAwareOptimizer(
            MockSolverService(),
            customers,
            get_test_vehicle_config(),
            get_test_params(),
        )
        scenarios = [
            {"name": "场景A", "solution": solution},
            {"name": "场景B", "solution": solution},
        ]
        result = optimizer.compare_carbon_scenarios(scenarios)
        assert "comparison" in result
        assert "best_scenario" in result
