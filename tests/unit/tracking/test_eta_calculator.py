"""
单元测试：tracking/eta_calculator.py — ETA 预估
"""

import pytest

from tracking.eta_calculator import calculate_eta


class TestETACalculator:
    def test_calculate_eta_zero_distance(self):
        """同一位置 ETA 应为 0。"""
        eta, minutes, distance = calculate_eta(39.9, 116.4, 39.9, 116.4)
        assert distance == 0.0
        assert minutes == 0.0

    def test_calculate_eta_known_distance(self):
        """已知距离的 ETA 计算。"""
        # 约 1.11 km（0.01度纬度 ≈ 1.11km）
        eta, minutes, distance = calculate_eta(39.9, 116.4, 39.91, 116.4, speed_kmh=40)
        assert distance == pytest.approx(1.11, rel=0.1)
        assert minutes == pytest.approx(1.67, rel=0.1)

    def test_calculate_eta_with_speed(self):
        """不同速度下 ETA 不同。"""
        _, minutes_fast, dist = calculate_eta(39.9, 116.4, 39.92, 116.4, speed_kmh=80)
        _, minutes_slow, _ = calculate_eta(39.9, 116.4, 39.92, 116.4, speed_kmh=40)
        assert minutes_fast < minutes_slow
        assert dist > 0

    def test_calculate_eta_returns_timestamp(self):
        """验证返回时间戳类型。"""
        from datetime import datetime
        eta, _, _ = calculate_eta(39.9, 116.4, 39.91, 116.4)
        assert isinstance(eta, datetime)
