"""
单元测试：analysis/comparison.py — 多场景对比分析
"""

import pytest
from analysis.comparison import ScenarioComparison
from tests.fixtures.customers import get_minimal_solution


def make_solution(cost: float = 500.0, carbon: float = 25.0,
                  distance: float = 100.0, vehicles: int = 2,
                  name: str = "") -> dict:
    """生成指定参数的结果 dict（含 cost_data 和 solution_data）。"""
    return {
        "cost_data": {
            "total_cost": cost,
            "transport_cost": cost * 0.4,
            "fixed_cost": cost * 0.2,
            "labor_cost": cost * 0.25,
            "carbon_cost": cost * 0.1,
            "penalty_cost": cost * 0.05,
            "carbon_emission_kg": carbon,
            "total_distance_km": distance,
            "total_time_min": 120,
            "total_late_minutes": 0,
        },
        "solution_data": {
            "routes": [],
            "total_distance": distance,
            "vehicles_used": {"4.2m": vehicles},
            "total_late_minutes": 0,
        },
    }


class TestScenarioComparison:
    def test_compare_two(self):
        s1 = make_solution(cost=500, name="A")
        s2 = make_solution(cost=600, name="B")
        result = ScenarioComparison().compare_solutions(
            [s1, s2], scenario_names=["方案A", "方案B"])
        assert len(result.scenarios) == 2
        assert result.scenarios == ["方案A", "方案B"]

    def test_three_scenarios(self):
        scenarios = [make_solution(cost=i * 100 + 300) for i in range(3)]
        result = ScenarioComparison().compare_solutions(
            scenarios, scenario_names=["A", "B", "C"])
        assert len(result.scenarios) == 3

    def test_auto_names(self):
        s1, s2 = make_solution(cost=500), make_solution(cost=600)
        result = ScenarioComparison().compare_solutions([s1, s2])
        assert result.scenarios == ["场景1", "场景2"]

    def test_metrics_keys(self):
        s1, s2 = make_solution(cost=500), make_solution(cost=600)
        result = ScenarioComparison().compare_solutions([s1, s2])
        expected = {"total_cost", "carbon_emission_kg", "total_distance_km",
                     "vehicle_count", "total_time_min"}
        assert set(result.metrics.keys()) == expected

    def test_radar_chart(self):
        sc = ScenarioComparison()
        s1, s2 = make_solution(cost=500), make_solution(cost=600)
        result = sc.compare_solutions([s1, s2])
        fig = sc.generate_radar_chart(result)
        if fig is not None:
            assert len(fig.data) == 2

    def test_bar_chart(self):
        sc = ScenarioComparison()
        s1, s2 = make_solution(cost=500), make_solution(cost=600)
        result = sc.compare_solutions([s1, s2])
        fig = sc.generate_bar_comparison(result)
        if fig is not None:
            assert len(fig.data) > 0

    def test_heatmap(self):
        sc = ScenarioComparison()
        s1, s2 = make_solution(cost=500), make_solution(cost=600)
        result = sc.compare_solutions([s1, s2])
        fig = sc.generate_heatmap(result)
        if fig is not None:
            assert len(fig.data) > 0

    def test_report(self):
        sc = ScenarioComparison()
        s1 = make_solution(cost=500)
        s2 = make_solution(cost=800)
        result = sc.compare_solutions([s1, s2], scenario_names=["低本", "高本"])
        report = sc.generate_comparison_report(result)
        assert "多场景对比分析报告" in report

    def test_to_dict(self):
        s1, s2 = make_solution(cost=500), make_solution(cost=600)
        result = ScenarioComparison().compare_solutions([s1, s2])
        d = result.to_dict()
        assert "scenarios" in d
        assert len(d["scenarios"]) == 2
