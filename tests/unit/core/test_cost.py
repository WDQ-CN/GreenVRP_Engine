"""
单元测试：core/cost.py
"""

import pytest

from core.cost import (
    VehicleCostParams,
    _build_vehicle_params,
    calculate_cost_efficiency_metrics,
    calculate_green_cost,
    calculate_green_cost_batch,
    format_cost_report,
)
from tests.fixtures.customers import get_minimal_solution, get_test_params, get_test_vehicle_config


class TestBuildVehicleParams:
    def test_build_params(self):
        config = get_test_vehicle_config()
        params = _build_vehicle_params(config)
        assert "4.2m" in params
        assert isinstance(params["4.2m"], VehicleCostParams)
        assert params["4.2m"].fuel_coefficient == 12 / 100.0


class TestCalculateGreenCost:
    def test_minimal_solution(self):
        solution = get_minimal_solution()
        config = get_test_vehicle_config()
        params = get_test_params()
        result = calculate_green_cost(solution, config, params)

        assert "total_cost" in result
        assert "transport_cost" in result
        assert "labor_cost" in result
        assert "fixed_cost" in result
        assert "penalty_cost" in result
        assert "carbon_cost" in result
        assert "carbon_emission_kg" in result
        assert result["total_cost"] > 0
        assert result["carbon_emission_kg"] >= 0

    def test_empty_solution(self):
        solution = {
            "routes": [],
            "total_distance": 0,
            "vehicles_used": {},
            "total_late_minutes": 0,
            "solution_status": "SUCCESS",
        }
        config = get_test_vehicle_config()
        params = get_test_params()
        result = calculate_green_cost(solution, config, params)
        assert result["total_cost"] == 0.0
        assert result["carbon_emission_kg"] == 0.0

    def test_late_penalty(self):
        solution = get_minimal_solution()
        solution["total_late_minutes"] = 30
        config = get_test_vehicle_config()
        params = get_test_params()
        result = calculate_green_cost(solution, config, params)
        assert result["penalty_cost"] == pytest.approx(300.0, abs=1e-6)

    def test_cost_breakdown_sum(self):
        solution = get_minimal_solution()
        config = get_test_vehicle_config()
        params = get_test_params()
        result = calculate_green_cost(solution, config, params)
        breakdown_sum = sum(result["cost_breakdown"].values())
        assert breakdown_sum == pytest.approx(result["total_cost"], abs=1e-3)


class TestCalculateGreenCostBatch:
    def test_batch(self):
        sol1 = get_minimal_solution()
        sol2 = get_minimal_solution()
        config = get_test_vehicle_config()
        params = get_test_params()
        results = calculate_green_cost_batch([sol1, sol2], config, params)
        assert len(results) == 2
        assert all("total_cost" in r for r in results)


class TestCalculateCostEfficiencyMetrics:
    def test_basic_metrics(self):
        solution = get_minimal_solution()
        config = get_test_vehicle_config()
        params = get_test_params()
        cost = calculate_green_cost(solution, config, params)
        metrics = calculate_cost_efficiency_metrics(cost, solution)
        assert "cost_per_km" in metrics
        assert "cost_per_customer" in metrics
        assert "carbon_per_km" in metrics
        assert "labor_efficiency" in metrics
        assert metrics["cost_per_km"] > 0

    def test_zero_distance_avoid_division_by_zero(self):
        solution = {
            "routes": [],
            "total_distance": 0,
            "vehicles_used": {},
            "total_late_minutes": 0,
            "solution_status": "SUCCESS",
        }
        cost = {
            "total_cost": 0,
            "total_distance_km": 0,
            "total_time_min": 0,
            "service_time_min": 0,
            "carbon_emission_kg": 0,
        }
        metrics = calculate_cost_efficiency_metrics(cost, solution)
        assert metrics["cost_per_km"] == 0.0
        assert metrics["cost_per_customer"] == 0.0


class TestFormatCostReport:
    def test_report_contains_key_info(self):
        solution = get_minimal_solution()
        config = get_test_vehicle_config()
        params = get_test_params()
        cost = calculate_green_cost(solution, config, params)
        report = format_cost_report(cost)
        assert "绿色物流成本核算报告" in report
        assert str(cost["total_cost"]) in report or f"{cost['total_cost']:.2f}" in report
