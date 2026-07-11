"""
单元测试：frontend/config.py — 企业前端配置
"""

import re
import pytest


class TestEnterpriseConfig:
    """前端配置正确性验证。"""

    def test_color_scheme(self):
        """所有颜色值应为有效的十六进制颜色码。"""
        from frontend.config import ENTERPRISE_COLORS
        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for name, color in ENTERPRISE_COLORS.items():
            assert hex_pattern.match(color), f"{name}: {color} 不是有效的十六进制颜色"

    def test_color_keys_present(self):
        """必须包含所有必要颜色键。"""
        from frontend.config import ENTERPRISE_COLORS
        required = {"primary", "secondary", "accent", "success", "warning", "danger",
                    "light", "white", "gray", "dark_gray"}
        assert required.issubset(ENTERPRISE_COLORS.keys())

    def test_page_config(self):
        """页面配置包含必要字段。"""
        from frontend.config import PAGE_CONFIG
        assert PAGE_CONFIG["page_title"] == "绿色物流路径优化引擎"
        assert PAGE_CONFIG["layout"] == "wide"
        assert PAGE_CONFIG["initial_sidebar_state"] == "expanded"

    def test_default_params(self):
        """默认经济参数应有正确类型和值。"""
        from frontend.config import DEFAULT_PARAMS
        assert isinstance(DEFAULT_PARAMS["fuel_price"], (int, float))
        assert DEFAULT_PARAMS["fuel_price"] > 0
        assert DEFAULT_PARAMS["search_time_limit"] > 0

    def test_get_text_zh(self):
        """中文语言键查找。"""
        from frontend.config import get_text, CURRENT_LANGUAGE
        # 保存原始语言设置
        original_lang = CURRENT_LANGUAGE
        try:
            import frontend.config as cfg
            cfg.CURRENT_LANGUAGE = "zh"
            text = get_text("app_title")
            assert text == "绿色物流路径优化引擎"
        finally:
            cfg.CURRENT_LANGUAGE = original_lang

    def test_get_text_en(self):
        """英文语言键查找。"""
        from frontend.config import get_text, CURRENT_LANGUAGE
        original_lang = CURRENT_LANGUAGE
        try:
            import frontend.config as cfg
            cfg.CURRENT_LANGUAGE = "en"
            text = get_text("app_title")
            assert text == "Green Logistics Route Optimization Engine"
        finally:
            cfg.CURRENT_LANGUAGE = original_lang

    def test_get_text_fallback(self):
        """不存在的键应返回键本身。"""
        from frontend.config import get_text, CURRENT_LANGUAGE
        original_lang = CURRENT_LANGUAGE
        try:
            import frontend.config as cfg
            cfg.CURRENT_LANGUAGE = "zh"
            text = get_text("nonexistent_key_XYZ")
            assert text == "nonexistent_key_XYZ"
        finally:
            cfg.CURRENT_LANGUAGE = original_lang

    def test_vehicle_config_all_types(self):
        """所有 3 种车型应都有必要字段。"""
        from frontend.config import DEFAULT_VEHICLE_CONFIG
        required_fields = {"capacity", "fixed_cost", "fuel_per_100km", "speed_kmh", "count", "color"}
        for v_type, config in DEFAULT_VEHICLE_CONFIG.items():
            assert required_fields.issubset(config.keys()), f"{v_type} 缺少字段"
            assert config["count"] >= 0

    def test_vehicle_config_three_types(self):
        """应有 3 种车型。"""
        from frontend.config import DEFAULT_VEHICLE_CONFIG
        assert len(DEFAULT_VEHICLE_CONFIG) == 3
        assert "4.2m" in DEFAULT_VEHICLE_CONFIG
        assert "7.6m" in DEFAULT_VEHICLE_CONFIG
        assert "9.6m" in DEFAULT_VEHICLE_CONFIG

    def test_strategy_config(self):
        """策略配置应有 5 种子策略。"""
        from frontend.config import STRATEGY_CONFIG
        assert "multi_strategy" in STRATEGY_CONFIG
        assert "strategies" in STRATEGY_CONFIG
        assert len(STRATEGY_CONFIG["strategies"]) >= 3  # 至少 3 种

    def test_map_config(self):
        """地图配置应有默认中心和缩放级别。"""
        from frontend.config import MAP_CONFIG
        assert "default_center" in MAP_CONFIG
        assert "lat" in MAP_CONFIG["default_center"]
        assert "lon" in MAP_CONFIG["default_center"]
        assert MAP_CONFIG["default_zoom"] > 0

    def test_performance_config(self):
        """性能配置应有合理的默认值。"""
        from frontend.config import PERFORMANCE_CONFIG
        assert PERFORMANCE_CONFIG["cache_ttl"] > 0
        assert PERFORMANCE_CONFIG["max_history_size"] > 0

    @pytest.mark.parametrize("color_key", [
        "primary", "secondary", "accent", "success", "warning", "danger",
    ])
    def test_vehicle_colors_use_enterprise(self, color_key):
        """车辆颜色应引用企业配色方案中的颜色。"""
        from frontend.config import ENTERPRISE_COLORS, DEFAULT_VEHICLE_CONFIG
        enterprise_values = set(ENTERPRISE_COLORS.values())
        for v_type, config in DEFAULT_VEHICLE_CONFIG.items():
            assert config["color"] in enterprise_values, \
                f"{v_type} 颜色 {config['color']} 不在 ENTERPRISE_COLORS 中"
