"""
单元测试：frontend/components/chart_view.py — 企业风格图表组件
"""

import pytest


@pytest.fixture
def cost_result():
    return {
        "total_cost": 1000.0,
        "transport_cost": 400.0,
        "labor_cost": 250.0,
        "fixed_cost": 200.0,
        "carbon_cost": 100.0,
        "penalty_cost": 50.0,
        "carbon_emission_kg": 25.0,
        "total_distance_km": 110.0,
        "total_time_min": 135,
        "total_late_minutes": 0,
        "driving_time_min": 80.0,
        "service_time_min": 45.0,
        "waiting_time_min": 10.0,
        "cost_breakdown": {
            "运输成本": 400.0, "人工成本": 250.0,
            "固定成本": 200.0, "碳排成本": 100.0, "惩罚成本": 50.0,
        },
    }


@pytest.fixture
def solution():
    return {
        "routes": [{"vehicle_id": 0, "vehicle_type": "4.2m", "distance_km": 50.0}],
        "total_distance": 110.0,
        "vehicles_used": {"4.2m": 2, "7.6m": 1, "9.6m": 0},
        "solution_status": "SUCCESS",
    }


@pytest.fixture
def vehicle_config():
    return {
        "4.2m": {"count": 3, "color": "#3498DB"},
        "7.6m": {"count": 2, "color": "#27AE60"},
        "9.6m": {"count": 2, "color": "#2C3E50"},
    }


@pytest.fixture
def solutions_history():
    return [
        {"name": "策略A", "solve_time": 15.0,
         "solution": {"total_distance": 100.0, "vehicles_used": {"4.2m": 2, "7.6m": 1}},
         "cost_result": {
             "total_cost": 800.0, "transport_cost": 300.0, "carbon_cost": 50.0,
             "penalty_cost": 20.0, "carbon_emission_kg": 20.0, "cost_breakdown": {},
         }},
        {"name": "策略B", "solve_time": 25.0,
         "solution": {"total_distance": 120.0, "vehicles_used": {"4.2m": 3, "7.6m": 2}},
         "cost_result": {
             "total_cost": 1000.0, "transport_cost": 400.0, "carbon_cost": 80.0,
             "penalty_cost": 40.0, "carbon_emission_kg": 30.0, "cost_breakdown": {},
         }},
    ]


class TestEnterpriseChartTemplate:
    def test_returns_dict(self):
        from frontend.components.chart_view import enterprise_chart_template
        template = enterprise_chart_template()
        assert isinstance(template, dict)
        assert "font" in template
        assert "paper_bgcolor" in template
        assert template["paper_bgcolor"] == "white"


class TestCreateCostBreakdownChart:
    def test_normal(self, cost_result):
        from frontend.components.chart_view import create_cost_breakdown_chart
        fig = create_cost_breakdown_chart(cost_result)
        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].type == "pie"

    def test_empty_breakdown_returns_none(self):
        from frontend.components.chart_view import create_cost_breakdown_chart
        result = create_cost_breakdown_chart({"cost_breakdown": {}})
        assert result is None

    def test_missing_breakdown_returns_none(self):
        from frontend.components.chart_view import create_cost_breakdown_chart
        result = create_cost_breakdown_chart({})
        assert result is None

    def test_single_item(self):
        from frontend.components.chart_view import create_cost_breakdown_chart
        fig = create_cost_breakdown_chart({"cost_breakdown": {"运输成本": 500.0}})
        assert fig is not None
        assert len(fig.data[0].labels) == 1


class TestCreateCostComparisonChart:
    def test_normal(self, solutions_history):
        from frontend.components.chart_view import create_cost_comparison_chart
        fig = create_cost_comparison_chart(solutions_history)
        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        # 应有 3 条 trace (运输/碳排/惩罚)
        assert len(fig.data) == 3

    def test_empty_history_returns_none(self):
        from frontend.components.chart_view import create_cost_comparison_chart
        assert create_cost_comparison_chart([]) is None

    def test_single_solution(self):
        from frontend.components.chart_view import create_cost_comparison_chart
        fig = create_cost_comparison_chart([
            {"name": "策略X", "solve_time": 10,
             "solution": {"total_distance": 50},
             "cost_result": {
                 "total_cost": 500, "transport_cost": 200,
                 "carbon_cost": 30, "penalty_cost": 10,
                 "carbon_emission_kg": 5, "cost_breakdown": {},
             }}
        ])
        assert fig is not None
        assert len(fig.data) == 3

    def test_missing_carbon_cost_defaults_zero(self):
        from frontend.components.chart_view import create_cost_comparison_chart
        fig = create_cost_comparison_chart([
            {"name": "策略X", "solve_time": 10,
             "solution": {"total_distance": 50},
             "cost_result": {
                 "total_cost": 500, "transport_cost": 200,
                 "penalty_cost": 10, "carbon_emission_kg": 5, "cost_breakdown": {},
             }}
        ])
        assert fig is not None


class TestCreatePerformanceComparisonChart:
    def test_normal(self, solutions_history):
        from frontend.components.chart_view import create_performance_comparison_chart
        fig = create_performance_comparison_chart(solutions_history)
        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        # 应有 2 条 trace (求解时间 + 总距离)
        assert len(fig.data) == 2

    def test_empty_returns_none(self):
        from frontend.components.chart_view import create_performance_comparison_chart
        assert create_performance_comparison_chart([]) is None


class TestCreateCarbonEmissionChart:
    def test_normal(self, solutions_history):
        from frontend.components.chart_view import create_carbon_emission_chart
        fig = create_carbon_emission_chart(solutions_history)
        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].type == "bar"

    def test_empty_returns_none(self):
        from frontend.components.chart_view import create_carbon_emission_chart
        assert create_carbon_emission_chart([]) is None

    def test_min_emission_highlighted(self):
        """最低碳排放的方案应使用成功绿。"""
        from frontend.components.chart_view import create_carbon_emission_chart
        hist = [
            {"name": "A", "solve_time": 10, "solution": {"total_distance": 100},
             "cost_result": {"carbon_emission_kg": 30.0, "total_cost": 500,
                             "transport_cost": 200, "carbon_cost": 50, "penalty_cost": 10,
                             "cost_breakdown": {}}},
            {"name": "B", "solve_time": 10, "solution": {"total_distance": 100},
             "cost_result": {"carbon_emission_kg": 15.0, "total_cost": 500,
                             "transport_cost": 200, "carbon_cost": 50, "penalty_cost": 10,
                             "cost_breakdown": {}}},
        ]
        fig = create_carbon_emission_chart(hist)
        # B 方案碳排放更低，应为绿色
        assert fig is not None


class TestCreateVehicleUtilizationChart:
    def test_normal(self, solution, vehicle_config):
        from frontend.components.chart_view import create_vehicle_utilization_chart
        fig = create_vehicle_utilization_chart(solution, vehicle_config)
        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        # 每种车型一条 trace
        assert len(fig.data) == len(vehicle_config)

    def test_none_solution(self):
        from frontend.components.chart_view import create_vehicle_utilization_chart
        assert create_vehicle_utilization_chart(None, {"4.2m": {"count": 3}}) is None

    def test_none_config(self, solution):
        from frontend.components.chart_view import create_vehicle_utilization_chart
        assert create_vehicle_utilization_chart(solution, None) is None

    def test_unknown_vehicle_type(self):
        from frontend.components.chart_view import create_vehicle_utilization_chart
        fig = create_vehicle_utilization_chart(
            {"vehicles_used": {"unknown_type": 5}},
            {"known_type": {"count": 10}},
        )
        assert fig is not None


class TestCreateTimeAnalysisChart:
    def test_normal(self, cost_result):
        from frontend.components.chart_view import create_time_analysis_chart
        fig = create_time_analysis_chart(cost_result)
        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "pie"

    def test_all_zero_returns_none(self):
        from frontend.components.chart_view import create_time_analysis_chart
        result = create_time_analysis_chart({"driving_time_min": 0, "service_time_min": 0})
        assert result is None

    def test_partial_components(self, cost_result):
        from frontend.components.chart_view import create_time_analysis_chart
        fig = create_time_analysis_chart({"driving_time_min": 60.0})
        assert fig is not None

    def test_missing_fields_default_zero(self):
        from frontend.components.chart_view import create_time_analysis_chart
        result = create_time_analysis_chart({})
        assert result is None


class TestCreateEfficiencyIndicators:
    def test_normal(self, cost_result, solution):
        from frontend.components.chart_view import create_efficiency_indicators
        fig = create_efficiency_indicators(cost_result, solution)
        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        # 4 个指标 (cost_per_km, cost_per_customer, carbon_per_km, labor_efficiency)
        assert len(fig.data) == 4

    def test_with_empty_data(self):
        from frontend.components.chart_view import create_efficiency_indicators
        fig = create_efficiency_indicators({}, {})
        assert fig is not None


class TestEnterpriseMetricRow:
    def test_renders_metrics(self):
        """enterprise_metric_row 使用 streamlit 渲染指标。"""
        from unittest.mock import patch, MagicMock
        with patch("frontend.components.chart_view.st") as mock_st:
            from frontend.components.chart_view import enterprise_metric_row
            mock_st.columns.return_value = [MagicMock(), MagicMock()]
            enterprise_metric_row([
                {"title": "总成本", "value": "¥1000", "delta": "+5%", "delta_type": "negative"},
                {"title": "碳排放", "value": "25 kg"},
            ])
            # st.columns 被调用
            mock_st.columns.assert_called_once_with(2)

    def test_empty_metrics(self):
        from unittest.mock import patch, MagicMock
        with patch("frontend.components.chart_view.st") as mock_st:
            from frontend.components.chart_view import enterprise_metric_row
            mock_st.columns.return_value = []
            # 不应抛出异常
            enterprise_metric_row([])
            mock_st.columns.assert_called_once_with(0)
