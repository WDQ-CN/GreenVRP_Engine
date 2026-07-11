"""
单元测试：frontend/components/map_view.py — 企业风格地图组件
"""

import pandas as pd
import pytest


@pytest.fixture
def customers_df():
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
def solution():
    return {
        "routes": [
            {
                "vehicle_id": 0,
                "vehicle_type": "4.2m",
                "stops": [
                    {"node": 0, "customer_name": "仓库", "lat": 39.9042, "lon": 116.4074,
                     "arrival_time": 480, "service_time": 0, "is_late": False,
                     "demand": 0, "tw_earliest": 480, "tw_latest": 960},
                    {"node": 1, "customer_name": "客户A", "lat": 39.9123, "lon": 116.3456,
                     "arrival_time": 520, "service_time": 15, "is_late": False,
                     "demand": 45, "tw_earliest": 500, "tw_latest": 600},
                ],
                "distance_km": 50.0,
                "total_demand": 45,
            },
        ],
        "vehicles_used": {"4.2m": 1, "7.6m": 0, "9.6m": 0},
        "total_distance": 50.0,
        "solution_status": "SUCCESS",
    }


class TestCreateEnterpriseMap:
    """create_enterprise_map 函数测试。"""

    def test_with_solution_and_df(self, customers_df, solution):
        """有 solution 和 customers_df 时的地图创建。"""
        from frontend.components.map_view import create_enterprise_map
        route_map = create_enterprise_map(customers_df, solution)
        import folium
        assert isinstance(route_map, folium.Map)
        html = route_map._repr_html_()
        assert "leaflet" in html.lower()
        assert "39.9042" in html

    def test_without_solution(self, customers_df):
        """无 solution 但有所在地图创建。"""
        from frontend.components.map_view import create_enterprise_map
        route_map = create_enterprise_map(customers_df)
        assert isinstance(route_map, __import__("folium").Map)
        html = route_map._repr_html_()
        assert "leaflet" in html.lower()

    def test_without_customers(self, solution):
        """无 customers_df 时使用默认中心点。"""
        from frontend.components.map_view import create_enterprise_map
        route_map = create_enterprise_map(None, solution)
        assert isinstance(route_map, __import__("folium").Map)

    def test_both_none(self):
        """两者都为 None 时仍应返回有效地图。"""
        from frontend.components.map_view import create_enterprise_map
        route_map = create_enterprise_map(None, None)
        assert isinstance(route_map, __import__("folium").Map)

    def test_with_late_stop(self, customers_df):
        """迟到的站点标记应为警告色。"""
        from frontend.components.map_view import create_enterprise_map
        sol_with_late = {
            "routes": [{
                "vehicle_id": 0, "vehicle_type": "4.2m",
                "stops": [
                    {"node": 0, "customer_name": "仓库", "lat": 39.9042, "lon": 116.4074,
                     "arrival_time": 480, "service_time": 0, "is_late": False,
                     "demand": 0, "tw_earliest": 480, "tw_latest": 960},
                    {"node": 1, "customer_name": "客户A", "lat": 39.9123, "lon": 116.3456,
                     "arrival_time": 620, "service_time": 15, "is_late": True,
                     "demand": 45, "tw_earliest": 500, "tw_latest": 600, "late_minutes": 20},
                ],
                "distance_km": 50.0, "total_demand": 45,
            }],
            "vehicles_used": {"4.2m": 1},
            "total_distance": 50.0, "solution_status": "SUCCESS",
        }
        route_map = create_enterprise_map(customers_df, sol_with_late)
        html = route_map._repr_html_()
        # 应包含警告色 (#F39C12)
        assert "F39C12" in html

    def test_with_vehicle_config(self, customers_df, solution):
        """传入 vehicle_config 不应影响地图创建。"""
        from frontend.components.map_view import create_enterprise_map
        vc = {"4.2m": {"color": "#3498DB"}}
        route_map = create_enterprise_map(customers_df, solution, vc)
        assert isinstance(route_map, __import__("folium").Map)


class TestDisplayRouteStatistics:
    """display_route_statistics 使用 streamlit 渲染。"""

    def test_with_solution(self, solution):
        from unittest.mock import patch, MagicMock
        with patch("frontend.components.map_view.st") as mock_st:
            mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
            from frontend.components.map_view import display_route_statistics
            display_route_statistics(solution)
            # 应调用 st.dataframe 渲染路线表
            mock_st.dataframe.assert_called_once()
            # 应调用 st.metric 3 次 (总距离, 服务客户数, 总迟到)
            assert mock_st.metric.call_count >= 3

    def test_without_solution(self):
        from unittest.mock import patch
        with patch("frontend.components.map_view.st") as mock_st:
            from frontend.components.map_view import display_route_statistics
            display_route_statistics({})
            # 无 routes 时不应渲染
            mock_st.dataframe.assert_not_called()

    def test_empty_routes(self):
        from unittest.mock import patch
        with patch("frontend.components.map_view.st") as mock_st:
            from frontend.components.map_view import display_route_statistics
            display_route_statistics({"routes": []})
            mock_st.dataframe.assert_not_called()

    def test_multiple_routes_add_distance(self):
        """多条路线的总距离应累加。"""
        from unittest.mock import patch, MagicMock
        sol = {
            "routes": [
                {"vehicle_id": 0, "vehicle_type": "4.2m", "distance_km": 30.0,
                 "stops": [{"node": 1}], "total_demand": 45, "late_minutes": 0},
                {"vehicle_id": 1, "vehicle_type": "7.6m", "distance_km": 40.0,
                 "stops": [{"node": 2}], "total_demand": 67, "late_minutes": 5},
            ]
        }
        with patch("frontend.components.map_view.st") as mock_st:
            mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
            from frontend.components.map_view import display_route_statistics
            display_route_statistics(sol)
            # 验证 st.metric 被调用时包含总距离 70.0
            calls = mock_st.metric.call_args_list
            assert any("70.00" in str(c) for c in calls)


class TestDisplayRouteDetails:
    """display_route_details 使用 streamlit 渲染。"""

    def test_with_solution(self, solution):
        from unittest.mock import patch, MagicMock
        with patch("frontend.components.map_view.st") as mock_st:
            mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
            from frontend.components.map_view import display_route_details
            display_route_details(solution)
            # 应调用 st.expander
            mock_st.expander.assert_called_once()

    def test_without_solution(self):
        from unittest.mock import patch
        with patch("frontend.components.map_view.st") as mock_st:
            from frontend.components.map_view import display_route_details
            display_route_details({})
            mock_st.expander.assert_not_called()

    def test_empty_routes(self):
        from unittest.mock import patch
        with patch("frontend.components.map_view.st") as mock_st:
            from frontend.components.map_view import display_route_details
            display_route_details({"routes": []})
            mock_st.expander.assert_not_called()


class TestEnterpriseSectionHeader:
    """enterprise_section_header 使用 streamlit 渲染。"""

    def test_renders_title(self):
        from unittest.mock import patch
        with patch("frontend.components.map_view.st") as mock_st:
            from frontend.components.map_view import enterprise_section_header
            enterprise_section_header("测试标题")
            mock_st.markdown.assert_called_once()
            # 标题应包含在 markdown 内容中
            args, kwargs = mock_st.markdown.call_args
            assert len(args) > 0
            assert "测试标题" in args[0]
            # unsafe_allow_html=True
            assert kwargs.get("unsafe_allow_html") is True
