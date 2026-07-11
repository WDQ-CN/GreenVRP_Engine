"""
单元测试：optimization/carbon_aware.py — 碳感知优化（纯函数部分）
"""

import pytest
from pytest import approx

from optimization.carbon_aware import CarbonAwareOptimizer, CarbonEfficiencyReport


def _make_report(total=100.0, per_km=0.5):
    return CarbonEfficiencyReport(
        total_carbon_kg=total,
        carbon_per_km=per_km,
        carbon_per_customer=5.0,
        carbon_per_kg_goods=0.1,
        vehicle_efficiency={"4.2m": per_km},
        reduction_potential=20.0,
        recommendations=["优化路线"],
    )


class TestCarbonEfficiencyReport:
    def test_create(self):
        r = _make_report()
        assert r.total_carbon_kg == 100.0
        assert r.carbon_per_km == 0.5

    def test_to_dict(self):
        r = _make_report()
        d = r.to_dict()
        assert d["total_carbon_kg"] == 100.0
        assert "4.2m" in d["vehicle_efficiency"]


class TestDetectSolverSignature:
    def test_new_signature(self):
        # 参数名包含 time_penalty 或 time_limit → 新签名
        def solver_with_time(customers_df, vehicle_config, time_penalty_per_min, time_limit):
            pass
        optimizer = CarbonAwareOptimizer(solver_with_time, [], {}, {"fuel_price": 7.5})
        assert optimizer._detect_solver_signature() == "new"

    def test_old_signature(self):
        # 普通 3 参数 → 旧签名
        def solver_old(customers, vehicle_config, params):
            pass
        optimizer = CarbonAwareOptimizer(solver_old, [], {}, {"fuel_price": 7.5})
        assert optimizer._detect_solver_signature() == "old"


class TestCalculateCarbonEfficiency:
    def test_basic(self):
        optimizer = CarbonAwareOptimizer(lambda *a: {}, [], {}, {"fuel_price": 7.5})
        solution = {
            "cost_data": {"carbon_emission_kg": 25.0, "total_distance_km": 100.0, "total_cost": 500.0},
            "routes": [{"vehicle_type": "4.2m", "distance_km": 100.0, "stops": [{"node": 1}]}],
        }
        report = optimizer.calculate_carbon_efficiency(solution)
        assert isinstance(report, CarbonEfficiencyReport)
        assert report.total_carbon_kg == approx(25.0)

    def test_empty_routes(self):
        optimizer = CarbonAwareOptimizer(lambda *a: {}, [], {}, {"fuel_price": 7.5})
        report = optimizer.calculate_carbon_efficiency(
            {"cost_data": {"carbon_emission_kg": 0.0, "total_distance_km": 0.0, "total_cost": 0.0},
             "routes": []},
        )
        assert report.total_carbon_kg == 0.0


class TestCompareCarbonScenarios:
    def test_compare_two(self):
        optimizer = CarbonAwareOptimizer(lambda *a: {}, [], {}, {"fuel_price": 7.5})
        scenarios = [
            {"name": "A", "solution": {
                "cost_data": {"carbon_emission_kg": 25.0, "total_distance_km": 100.0, "total_cost": 500},
                "routes": []}},
            {"name": "B", "solution": {
                "cost_data": {"carbon_emission_kg": 30.0, "total_distance_km": 120.0, "total_cost": 600},
                "routes": []}},
        ]
        results = optimizer.compare_carbon_scenarios(scenarios)
        assert len(results["comparison"]) == 2
