"""
单元测试：web_app.py — Streamlit Web UI（纯函数测试）
"""

import pandas as pd
import pytest


class TestInitSessionState:
    """init_session_state 逻辑测试。"""

    def test_defaults(self):
        """模拟会话状态初始化逻辑。"""
        from web_app import init_session_state
        # 模拟 session_state 行为
        class FakeSessionState:
            def __init__(self):
                self._store = {}
            def __contains__(self, key):
                return key in self._store
            def __getattr__(self, key):
                if key.startswith('_'):
                    raise AttributeError(key)
                return self._store.get(key)
            def __setattr__(self, key, value):
                if key.startswith('_'):
                    super().__setattr__(key, value)
                else:
                    self._store[key] = value

        import web_app
        original_st = web_app.st
        try:
            web_app.st = type('MockSt', (), {'session_state': FakeSessionState()})()
            init_session_state()
            ss = web_app.st.session_state
            assert ss.solution is None
            assert ss.cost_result is None
            assert ss.customers_df is None
            assert ss.solve_time == 0
            assert ss.solutions_history == []
            assert ss.current_solution_name is None
        finally:
            web_app.st = original_st


class TestLoadDefaultData:
    """load_default_data 测试。"""

    def test_file_exists(self):
        with pytest.MonkeyPatch.context() as mp:
            mock_df = pd.DataFrame({"id": [0, 1]})
            mp.setattr("pandas.read_csv", lambda *a, **kw: mock_df)
            from web_app import load_default_data
            result = load_default_data()
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2

    def test_file_not_found_returns_sample(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("pandas.read_csv", lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError()))
            from web_app import load_default_data
            result = load_default_data()
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 6
            assert "id" in result.columns
            assert "lat" in result.columns


class TestCreateMap:
    """create_map 测试 — 验证返回类型。"""

    def test_without_solution(self):
        from web_app import create_map
        df = pd.DataFrame({
            "id": [0, 1], "lat": [39.9, 40.0], "lon": [116.4, 116.5], "name": ["仓库", "客户A"]
        })
        route_map = create_map(df)
        import folium
        assert isinstance(route_map, folium.Map)

    def test_with_solution(self):
        from web_app import create_map
        df = pd.DataFrame({
            "id": [0, 1], "lat": [39.9, 40.0], "lon": [116.4, 116.5], "name": ["仓库", "客户A"]
        })
        sol = {
            "routes": [{
                "vehicle_id": 0, "vehicle_type": "4.2m",
                "stops": [
                    {"node": 0, "lat": 39.9, "lon": 116.4, "is_late": False},
                    {"node": 1, "lat": 40.0, "lon": 116.5, "is_late": False,
                     "customer_name": "客户A", "demand": 45,
                     "arrival_time": 520, "tw_earliest": 500, "tw_latest": 600},
                ], "distance_km": 20.0,
            }]
        }
        route_map = create_map(df, sol)
        html = route_map._repr_html_()
        assert "leaflet" in html.lower()
        assert "39.9" in html

    def test_with_late_stop(self):
        from web_app import create_map
        df = pd.DataFrame({
            "id": [0, 1], "lat": [39.9, 40.0], "lon": [116.4, 116.5], "name": ["仓库", "客户A"]
        })
        sol = {
            "routes": [{
                "vehicle_id": 0, "vehicle_type": "4.2m",
                "stops": [
                    {"node": 0, "lat": 39.9, "lon": 116.4, "is_late": False},
                    {"node": 1, "lat": 40.0, "lon": 116.5, "is_late": True, "late_minutes": 15,
                     "customer_name": "客户A", "demand": 45,
                     "arrival_time": 620, "tw_earliest": 500, "tw_latest": 600},
                ], "distance_km": 20.0,
            }]
        }
        route_map = create_map(df, sol)
        html = route_map._repr_html_()
        assert "orange" in html.lower() or "FFA500" in html or "F39C12" in html


class TestGetAvailableStrategies:
    """get_available_strategies 测试。"""

    def test_returns_multiple_strategies(self):
        from web_app import get_available_strategies
        strategies = get_available_strategies()
        assert len(strategies) >= 4
        assert "多策略最优" in strategies
        for name, info in strategies.items():
            assert "desc" in info

    def test_strategy_structure(self):
        from web_app import get_available_strategies
        strategies = get_available_strategies()
        has_func = any("func" in info for info in strategies.values())
        has_params = any("strategy" in info and "meta" in info for info in strategies.values())
        assert has_func
        assert has_params


class TestSolveWithStrategy:
    """solve_with_strategy 测试。"""

    def test_func_strategy(self):
        from unittest.mock import MagicMock
        from web_app import solve_with_strategy
        mock_func = MagicMock(return_value={"solution_status": "SUCCESS", "routes": []})
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("web_app.GreenVRPSolver", MagicMock())
            result = solve_with_strategy(MagicMock(), MagicMock(), 10.0, 30, {"func": mock_func})
            mock_func.assert_called_once()
            assert result["solution_status"] == "SUCCESS"

    def test_exception_returns_error(self):
        from unittest.mock import MagicMock
        from web_app import solve_with_strategy
        mock_func = MagicMock(side_effect=ValueError("求解失败"))
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("web_app.GreenVRPSolver", MagicMock())
            result = solve_with_strategy(MagicMock(), MagicMock(), 10.0, 30, {"func": mock_func})
            assert "ERROR" in result["solution_status"]
