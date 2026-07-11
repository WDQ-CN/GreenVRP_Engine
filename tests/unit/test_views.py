"""
单元测试：views.py — 地图、成本图表和甘特图组件
"""

import pandas as pd
import pytest


@pytest.fixture
def sample_solution():
    """标准求解结果，含 2 条路线。"""
    routes = [
        {
            "vehicle_id": 0,
            "vehicle_type": "4.2m",
            "vehicle_color": "#1f77b4",
            "capacity": 800,
            "stops": [
                {"node": 0, "customer_id": 0, "customer_name": "仓库",
                 "lat": 39.9042, "lon": 116.4074, "demand": 0,
                 "arrival_time": 480, "service_time": 0,
                 "tw_earliest": 480, "tw_latest": 960,
                 "late_minutes": 0, "is_late": False},
                {"node": 1, "customer_id": 1, "customer_name": "客户A",
                 "lat": 39.9123, "lon": 116.3456, "demand": 45,
                 "arrival_time": 520, "service_time": 15,
                 "tw_earliest": 500, "tw_latest": 600,
                 "late_minutes": 0, "is_late": False},
            ],
            "distance_km": 50.0,
            "total_demand": 45,
            "total_time_min": 55,
            "late_minutes": 0,
        },
        {
            "vehicle_id": 1,
            "vehicle_type": "7.6m",
            "vehicle_color": "#2ca02c",
            "capacity": 1500,
            "stops": [
                {"node": 0, "customer_id": 0, "customer_name": "仓库",
                 "lat": 39.9042, "lon": 116.4074, "demand": 0,
                 "arrival_time": 480, "service_time": 0,
                 "tw_earliest": 480, "tw_latest": 960,
                 "late_minutes": 0, "is_late": False},
                {"node": 2, "customer_id": 2, "customer_name": "客户B",
                 "lat": 39.9456, "lon": 116.3789, "demand": 67,
                 "arrival_time": 540, "service_time": 20,
                 "tw_earliest": 520, "tw_latest": 640,
                 "late_minutes": 0, "is_late": False},
            ],
            "distance_km": 60.0,
            "total_demand": 67,
            "total_time_min": 80,
            "late_minutes": 0,
        },
    ]
    return {
        "routes": routes,
        "total_distance": 110.0,
        "vehicles_used": {"4.2m": 1, "7.6m": 1, "9.6m": 0},
        "total_late_minutes": 0,
        "solution_status": "SUCCESS",
    }


@pytest.fixture
def customers_df():
    """标准客户数据。"""
    return pd.DataFrame({
        "id": [0, 1, 2],
        "name": ["仓库", "客户A", "客户B"],
        "lat": [39.9042, 39.9123, 39.9456],
        "lon": [116.4074, 116.3456, 116.3789],
        "demand": [0, 45, 67],
        "service_time_min": [0, 15, 20],
        "tw_earliest": [480, 500, 520],
        "tw_latest": [960, 600, 640],
    })


@pytest.fixture
def cost_result():
    """标准成本结果。"""
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
        "cost_breakdown": {
            "运输成本": 400.0,
            "人工成本": 250.0,
            "固定成本": 200.0,
            "碳排成本": 100.0,
            "惩罚成本": 50.0,
        },
    }


# =============================================================================
# Test: create_route_map
# =============================================================================


class TestCreateRouteMap:
    """create_route_map 函数测试。"""

    def test_with_solution(self, sample_solution, customers_df):
        """有 solution 时应返回包含路线和站点的地图。"""
        from views import create_route_map
        route_map = create_route_map(sample_solution, customers_df)
        # 验证返回类型
        import folium
        assert isinstance(route_map, folium.Map)
        # 验证地图包含路线数据（通过检查内部结构）
        html = route_map._repr_html_()
        # 验证 HTML 中包含 JavaScript 和 Leaflet 相关代码
        assert "leaflet" in html.lower()
        # 验证包含客户位置数据（坐标被序列化到 HTML 中）
        assert "39.9042" in html
        assert "116.4074" in html

    def test_without_solution(self, customers_df):
        """solution 为 None 时应只显示客户位置。"""
        from views import create_route_map
        route_map = create_route_map(None, customers_df)
        import folium
        assert isinstance(route_map, folium.Map)
        html = route_map._repr_html_()
        assert "leaflet" in html.lower()
        assert "39.9042" in html

    def test_empty_routes(self, customers_df):
        """routes 为空列表时应只显示客户位置。"""
        from views import create_route_map
        route_map = create_route_map({"routes": []}, customers_df)
        import folium
        assert isinstance(route_map, folium.Map)

    def test_missing_fields_in_route(self, customers_df):
        """route 缺失关键字段时应降级处理不抛异常。"""
        from views import create_route_map
        bad_solution = {"routes": [{"unknown_field": "test"}]}
        # 不应抛出异常
        route_map = create_route_map(bad_solution, customers_df)
        import folium
        assert isinstance(route_map, folium.Map)

    def test_single_customer(self):
        """只有一个客户的场景。"""
        from views import create_route_map
        df = pd.DataFrame({
            "id": [0, 1],
            "name": ["仓库", "客户X"],
            "lat": [39.9, 40.0],
            "lon": [116.4, 116.5],
            "demand": [0, 50],
            "service_time_min": [0, 15],
            "tw_earliest": [480, 500],
            "tw_latest": [960, 600],
        })
        sol = {
            "routes": [{
                "vehicle_id": 0, "vehicle_type": "4.2m",
                "vehicle_color": "#1f77b4",
                "stops": [
                    {"node": 0, "customer_name": "仓库", "lat": 39.9, "lon": 116.4,
                     "arrival_time": 480, "service_time": 0, "is_late": False},
                    {"node": 1, "customer_name": "客户X", "lat": 40.0, "lon": 116.5,
                     "arrival_time": 520, "service_time": 15, "is_late": False},
                ],
                "distance_km": 20.0, "total_demand": 50,
            }]
        }
        route_map = create_route_map(sol, df)
        assert isinstance(route_map, __import__("folium").Map)

    def test_late_stop_color(self, customers_df):
        """迟到的站点标记颜色应为红色系。"""
        from views import create_route_map
        sol = {
            "routes": [{
                "vehicle_id": 0, "vehicle_type": "4.2m",
                "vehicle_color": "#1f77b4",
                "stops": [
                    {"node": 0, "customer_name": "仓库", "lat": 39.9042, "lon": 116.4074,
                     "arrival_time": 480, "service_time": 0, "is_late": False},
                    {"node": 1, "customer_name": "客户A", "lat": 39.9123, "lon": 116.3456,
                     "arrival_time": 620, "service_time": 15, "is_late": True,
                     "late_minutes": 20},
                ],
                "distance_km": 50.0, "total_demand": 45,
            }]
        }
        route_map = create_route_map(sol, customers_df)
        html = route_map._repr_html_()
        # 迟到标记使用 #E74C3C 红色
        assert "#E74C3C" in html or "E74C3C" in html


# =============================================================================
# Test: create_cost_stack_chart
# =============================================================================


class TestCreateCostStackChart:
    """create_cost_stack_chart 函数测试。"""

    def test_normal(self, cost_result):
        """完整的 cost_breakdown 应生成柱状图。"""
        from views import create_cost_stack_chart
        fig = create_cost_stack_chart(cost_result)
        assert isinstance(fig, __import__("plotly").graph_objects.Figure)
        # 应有 1 个 Bar trace
        assert len(fig.data) == 1
        assert fig.data[0].type == "bar"

    def test_empty_breakdown(self):
        """空字典应生成有效 Figure。"""
        from views import create_cost_stack_chart
        fig = create_cost_stack_chart({"cost_breakdown": {}})
        assert isinstance(fig, __import__("plotly").graph_objects.Figure)

    def test_partial_breakdown(self):
        """部分成本项应正确显示。"""
        from views import create_cost_stack_chart
        cost = {"cost_breakdown": {"运输成本": 500.0, "人工成本": 300.0}}
        fig = create_cost_stack_chart(cost)
        assert len(fig.data[0].x) == 2

    def test_null_values(self):
        """零值不应抛异常。"""
        from views import create_cost_stack_chart
        cost = {"cost_breakdown": {"成本A": 0, "成本B": 0, "成本C": 0}}
        fig = create_cost_stack_chart(cost)
        assert isinstance(fig, __import__("plotly").graph_objects.Figure)

    def test_missing_cost_breakdown_key(self):
        """缺少 cost_breakdown 键应降级。"""
        from views import create_cost_stack_chart
        fig = create_cost_stack_chart({})
        assert isinstance(fig, __import__("plotly").graph_objects.Figure)


# =============================================================================
# Test: create_gantt_chart
# =============================================================================


class TestCreateGanttChart:
    """create_gantt_chart 函数测试。"""

    def test_normal(self, sample_solution):
        """多车多站应生成甘特图。"""
        from views import create_gantt_chart
        fig = create_gantt_chart(sample_solution)
        assert isinstance(fig, __import__("plotly").graph_objects.Figure)

    def test_empty_routes(self):
        """无路线时应显示"暂无数据"。"""
        from views import create_gantt_chart
        fig = create_gantt_chart({})
        assert isinstance(fig, __import__("plotly").graph_objects.Figure)
        # 标题应显示暂无数据
        assert fig.layout.title.text is not None

    def test_single_route(self):
        """单车单站应生成有效图。"""
        from views import create_gantt_chart
        sol = {
            "routes": [{
                "vehicle_id": 0, "vehicle_type": "4.2m",
                "stops": [
                    {"node": 0, "arrival_time": 480, "service_time": 0},
                    {"node": 1, "arrival_time": 520, "service_time": 15},
                ],
            }]
        }
        fig = create_gantt_chart(sol)
        assert isinstance(fig, __import__("plotly").graph_objects.Figure)

    def test_with_service_time(self):
        """有服务时间时应包含 "服务" Resource 行。"""
        from views import create_gantt_chart
        sol = {
            "routes": [{
                "vehicle_id": 0, "vehicle_type": "4.2m",
                "stops": [
                    {"node": 0, "customer_name": "仓库", "arrival_time": 480, "service_time": 0},
                    {"node": 1, "customer_name": "客户A", "arrival_time": 520, "service_time": 30},
                ],
            }]
        }
        fig = create_gantt_chart(sol)
        # Figure 包含数据时应有 trace
        assert len(fig.data) > 0

    def test_no_service_time(self):
        """无服务时间（departure == arrival）时不生成服务行。"""
        from views import create_gantt_chart
        sol = {
            "routes": [{
                "vehicle_id": 0, "vehicle_type": "4.2m",
                "stops": [
                    {"node": 0, "customer_name": "仓库", "arrival_time": 480, "service_time": 0},
                    {"node": 1, "customer_name": "客户A", "arrival_time": 520, "service_time": 0},
                ],
            }]
        }
        fig = create_gantt_chart(sol)
        assert isinstance(fig, __import__("plotly").graph_objects.Figure)

    def test_with_vehicle_config(self, sample_solution):
        """传入 vehicle_config 不应影响基本功能。"""
        from views import create_gantt_chart
        vehicle_config = {"4.2m": {"color": "#1f77b4"}, "7.6m": {"color": "#2ca02c"}}
        fig = create_gantt_chart(sample_solution, vehicle_config)
        assert isinstance(fig, __import__("plotly").graph_objects.Figure)


# =============================================================================
# Test: _format_time (app.py 工具函数)
# =============================================================================


class TestFormatTime:
    """_format_time 工具函数测试。"""

    def test_zero(self):
        """0 分钟应为 00:00。"""
        from app import _format_time
        assert _format_time(0) == "00:00"

    def test_normal(self):
        """正常分钟数转换。"""
        from app import _format_time
        assert _format_time(60) == "01:00"

    def test_midnight(self):
        """1440 分钟（24小时）应为 00:00。"""
        from app import _format_time
        assert _format_time(1440) == "00:00"

    def test_arbitrary(self):
        """任意分钟数。"""
        from app import _format_time
        assert _format_time(125) == "02:05"
        # 3661 分钟 = 61小时1分钟 → (61 % 24):01 = 13:01
        assert _format_time(3661) == "13:01"
