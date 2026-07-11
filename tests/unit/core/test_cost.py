"""
单元测试：core/cost.py — 五维成本核算
"""

import pytest
from pytest import approx

from core.cost import (
    _build_vehicle_params,
    _get_vehicle_params_cached,
    calculate_cost_efficiency_metrics,
    calculate_green_cost,
    calculate_green_cost_batch,
    format_cost_report,
)
from tests.fixtures.customers import (
    get_minimal_solution,
    get_multi_route_solution,
    get_solution_with_late_customer,
    get_test_params,
    get_test_vehicle_config,
)


class TestBuildVehicleParams:
    def test_build_params(self):
        result = _build_vehicle_params(get_test_vehicle_config())
        assert "4.2m" in result
        assert "7.6m" in result
        p = result["4.2m"]
        assert p.fuel_coefficient == approx(12 / 100)
        assert p.speed_kmh == 40

    def test_empty_config(self):
        assert _build_vehicle_params({}) == {}

    def test_single_type(self):
        config = {"4.2m": {"fuel_per_100km": 12, "speed_kmh": 40}}
        result = _build_vehicle_params(config)
        assert result["4.2m"].speed_kmh == 40


class TestCalculateGreenCost:
    def test_minimal_solution(self):
        result = calculate_green_cost(
            get_minimal_solution(), get_test_vehicle_config(), get_test_params()
        )
        assert result["total_cost"] > 0
        assert result["transport_cost"] >= 0
        assert result["carbon_emission_kg"] >= 0
        assert result["total_distance_km"] == approx(10.0)

    def test_cost_breakdown_sum(self):
        result = calculate_green_cost(
            get_minimal_solution(), get_test_vehicle_config(), get_test_params()
        )
        b = result["cost_breakdown"]
        total = b["运输变动成本"] + b["人工时间成本"] + b["车辆固定成本"] \
                + b["违约惩罚成本"] + b["碳排放成本"]
        assert result["total_cost"] == approx(total)

    def test_multi_route(self):
        result = calculate_green_cost(
            get_multi_route_solution(), get_test_vehicle_config(), get_test_params()
        )
        assert result["total_distance_km"] == approx(25.0)

    def test_late_penalty(self):
        result = calculate_green_cost(
            get_solution_with_late_customer(), get_test_vehicle_config(), get_test_params()
        )
        assert result["penalty_cost"] == approx(500.0)  # 50 min * 10

    def test_empty_solution(self):
        result = calculate_green_cost(
            {"routes": [], "total_distance": 0}, get_test_vehicle_config(), get_test_params()
        )
        assert result["total_cost"] == 0.0
        assert result["carbon_emission_kg"] == 0.0

    def test_missing_vehicle_type(self):
        s = get_minimal_solution()
        del s["routes"][0]["vehicle_type"]
        result = calculate_green_cost(s, get_test_vehicle_config(), get_test_params())
        # 路线被跳过，无运输和变动成本，但固定成本可能仍计入
        assert result["transport_cost"] == 0.0

    def test_unknown_vehicle_type(self):
        s = get_minimal_solution()
        s["routes"][0]["vehicle_type"] = "unknown"
        result = calculate_green_cost(s, get_test_vehicle_config(), get_test_params())
        # 未知车型，路线被跳过
        assert result["transport_cost"] == 0.0

    def test_custom_params(self):
        s = get_minimal_solution()
        config = get_test_vehicle_config()
        high_fuel = get_test_params()
        high_fuel["fuel_price"] = 15.0
        r1 = calculate_green_cost(s, config, get_test_params())
        r2 = calculate_green_cost(s, config, high_fuel)
        assert r2["transport_cost"] > r1["transport_cost"]


class TestCalculateGreenCostBatch:
    def test_batch(self):
        results = calculate_green_cost_batch(
            [get_minimal_solution(), get_minimal_solution()],
            get_test_vehicle_config(), get_test_params(),
        )
        assert len(results) == 2

    def test_empty(self):
        assert calculate_green_cost_batch([], {}, {}) == []


class TestCalculateCostEfficiencyMetrics:
    def test_basic(self):
        cost_result = calculate_green_cost(
            get_minimal_solution(), get_test_vehicle_config(), get_test_params()
        )
        metrics = calculate_cost_efficiency_metrics(cost_result, get_minimal_solution())
        assert isinstance(metrics, dict)
        # 4 expected keys
        for k in ("cost_per_km", "cost_per_customer", "carbon_per_km", "labor_efficiency"):
            assert k in metrics

    def test_zero_distance(self):
        cost_result = calculate_green_cost(
            {"routes": [], "total_distance": 0}, get_test_vehicle_config(), get_test_params()
        )
        metrics = calculate_cost_efficiency_metrics(cost_result, {"routes": []})
        assert metrics["cost_per_km"] == 0.0


class TestFormatCostReport:
    def test_report_content(self):
        cost_result = calculate_green_cost(
            get_minimal_solution(), get_test_vehicle_config(), get_test_params()
        )
        report = format_cost_report(cost_result)
        assert "绿色物流成本核算报告" in report
        assert str(cost_result["total_cost"]) in report


class TestGetVehicleParamsCached:
    def test_cache_consistent(self):
        config = get_test_vehicle_config()
        r1 = _get_vehicle_params_cached(config)
        r2 = _get_vehicle_params_cached(config)
        assert r1 == r2

    def test_diff_configs(self):
        ca = {"4.2m": {"capacity": 800, "fixed_cost": 200,
                        "fuel_per_100km": 12, "speed_kmh": 40, "count": 2}}
        cb = get_test_vehicle_config()
        assert len(_get_vehicle_params_cached(ca)) != len(_get_vehicle_params_cached(cb))
