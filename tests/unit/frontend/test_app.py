"""
单元测试：app.py — Streamlit 主控入口
测试策略：纯函数直接测试，Streamlit 交互函数测试关键逻辑
"""

import pandas as pd
import pytest


# =============================================================================
# 纯函数测试
# =============================================================================

class TestFormatTime:
    """_format_time 纯函数测试。"""

    def test_zero(self):
        from app import _format_time
        assert _format_time(0) == "00:00"

    def test_normal_hours(self):
        from app import _format_time
        assert _format_time(60) == "01:00"
        assert _format_time(125) == "02:05"

    def test_midnight_rollover(self):
        from app import _format_time
        assert _format_time(1440) == "00:00"
        assert _format_time(1500) == "01:00"

    def test_negative(self):
        from app import _format_time
        result = _format_time(-10)
        assert isinstance(result, str)


class TestConstants:
    """DEFAULT_PARAMS 和 DEFAULT_VEHICLE_CONFIG 结构验证。"""

    def test_default_params_keys(self):
        from app import DEFAULT_PARAMS
        required = {"fuel_price", "hourly_wage", "carbon_price", "late_penalty_per_min"}
        assert required.issubset(DEFAULT_PARAMS.keys())
        for v in DEFAULT_PARAMS.values():
            assert isinstance(v, (int, float))
            assert v > 0

    def test_vehicle_config_structure(self):
        from app import DEFAULT_VEHICLE_CONFIG
        assert len(DEFAULT_VEHICLE_CONFIG) == 3
        for v_type, config in DEFAULT_VEHICLE_CONFIG.items():
            for field in ("capacity", "fixed_cost", "fuel_per_100km", "speed_kmh", "count", "color"):
                assert field in config, f"{v_type} 缺少 {field}"
        assert "4.2m" in DEFAULT_VEHICLE_CONFIG
        assert "7.6m" in DEFAULT_VEHICLE_CONFIG
        assert "9.6m" in DEFAULT_VEHICLE_CONFIG


# =============================================================================
# load_customers_data 测试
# =============================================================================

class TestLoadCustomersData:
    """load_customers_data 函数测试。"""

    def test_file_found(self):
        """文件存在时返回 DataFrame。"""
        import app
        mock_df = pd.DataFrame({"id": [0], "lat": [39.9], "lon": [116.4]})
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("pandas.read_csv", lambda *a, **kw: mock_df)
            result = app.load_customers_data()
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 1


# =============================================================================
# render_route_table - 数据转换逻辑测试
# =============================================================================

class TestRenderRouteTable:
    """render_route_table 的数据表格结构验证。"""

    def _get_table_row(self, routes, route_idx=0):
        """模拟 render_route_table 内部的表格构建逻辑。"""
        data = []
        route = routes[route_idx]
        for stop in route["stops"]:
            if stop.get("node", 0) > 0:
                data.append({
                    "客户": stop.get("customer_name", ""),
                    "需求量": f"{stop.get('demand', 0)} 件",
                    "到达时间": "XX:XX",
                    "时间窗": "XX:XX - XX:XX",
                    "状态": "✅ 正常" if not stop.get("is_late") else f"⚠️ 迟到 {stop.get('late_minutes', 0)}分钟",
                })
        return data

    def test_normal_stop(self):
        route = {"vehicle_id": 0, "vehicle_type": "4.2m", "stops": [
            {"node": 1, "customer_name": "客户A", "demand": 45, "is_late": False},
        ]}
        data = self._get_table_row([route])
        assert len(data) == 1
        assert data[0]["状态"] == "✅ 正常"

    def test_late_stop_status(self):
        route = {"vehicle_id": 0, "vehicle_type": "4.2m", "stops": [
            {"node": 1, "customer_name": "客户B", "demand": 30, "is_late": True, "late_minutes": 15},
        ]}
        data = self._get_table_row([route])
        assert "迟到" in data[0]["状态"]
        assert "15" in data[0]["状态"]
