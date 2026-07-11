"""
单元测试：analysis/comparison.py
"""

from analysis.comparison import ComparisonResult, ScenarioComparison
from tests.fixtures.customers import get_minimal_solution


def make_solution_with_cost(total_cost, carbon, distance, vehicles, total_time):
    sol = get_minimal_solution()
    sol["cost_data"] = {
        "total_cost": total_cost,
        "carbon_emission_kg": carbon,
        "total_distance_km": distance,
        "total_time_min": total_time,
    }
    sol["solution_data"] = {
        "total_distance": distance,
        "vehicles_used": vehicles,
    }
    return sol


class TestScenarioComparison:
    def test_compare_two_scenarios(self):
        comparison = ScenarioComparison()
        solutions = [
            make_solution_with_cost(1000, 50, 100, {"4.2m": 1}, 120),
            make_solution_with_cost(1200, 40, 110, {"4.2m": 1, "7.6m": 1}, 130),
        ]
        result = comparison.compare_solutions(solutions, scenario_names=["方案A", "方案B"])
        assert isinstance(result, ComparisonResult)
        assert result.best_scenario in ("方案A", "方案B")
        assert len(result.scenarios) == 2
        assert "total_cost" in result.metrics
        assert len(result.rankings["total_cost"]) == 2

    def test_compare_without_names(self):
        comparison = ScenarioComparison()
        solutions = [
            make_solution_with_cost(1000, 50, 100, {"4.2m": 1}, 120),
        ]
        result = comparison.compare_solutions(solutions)
        assert result.scenarios == ["场景1"]
        assert result.best_scenario == "场景1"

    def test_radar_chart_generation(self):
        comparison = ScenarioComparison()
        solutions = [
            make_solution_with_cost(1000, 50, 100, {"4.2m": 1}, 120),
            make_solution_with_cost(1200, 40, 110, {"4.2m": 1}, 130),
        ]
        result = comparison.compare_solutions(solutions)
        fig = comparison.generate_radar_chart(result)
        assert fig is not None
        assert len(fig.data) == 2

    def test_bar_comparison(self):
        comparison = ScenarioComparison()
        solutions = [
            make_solution_with_cost(1000, 50, 100, {"4.2m": 1}, 120),
            make_solution_with_cost(1200, 40, 110, {"4.2m": 1}, 130),
        ]
        result = comparison.compare_solutions(solutions)
        fig = comparison.generate_bar_comparison(result, metric="total_cost")
        assert fig is not None

    def test_heatmap(self):
        comparison = ScenarioComparison()
        solutions = [
            make_solution_with_cost(1000, 50, 100, {"4.2m": 1}, 120),
            make_solution_with_cost(1200, 40, 110, {"4.2m": 1}, 130),
        ]
        result = comparison.compare_solutions(solutions)
        fig = comparison.generate_heatmap(result)
        assert fig is not None

    def test_comparison_report(self):
        comparison = ScenarioComparison()
        solutions = [
            make_solution_with_cost(1000, 50, 100, {"4.2m": 1}, 120),
        ]
        result = comparison.compare_solutions(solutions)
        report = comparison.generate_comparison_report(result)
        assert "多场景对比分析报告" in report
        assert result.best_scenario in report

    def test_tradeoffs_analysis(self):
        comparison = ScenarioComparison()
        solutions = [
            make_solution_with_cost(1000, 50, 100, {"4.2m": 1}, 120),
            make_solution_with_cost(1200, 40, 110, {"4.2m": 1}, 130),
        ]
        result = comparison.compare_solutions(solutions)
        assert len(result.tradeoffs) > 0
        first = result.tradeoffs[0]
        assert "best_scenario" in first
        assert "worst_scenario" in first
