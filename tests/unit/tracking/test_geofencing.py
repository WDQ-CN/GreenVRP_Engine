"""
单元测试：tracking/geofencing.py — 电子围栏
"""

import pytest

from tracking.geofencing import Geofence, create_customer_geofence, create_depot_geofence


class TestGeofence:
    def test_contains_within_radius(self):
        # 仓库位置 (39.9, 116.4)，半径 1km
        fence = Geofence(39.9, 116.4, 1.0, "测试围栏")
        # 约 500米外
        assert fence.contains(39.905, 116.4) is True

    def test_not_contains_outside_radius(self):
        fence = Geofence(39.9, 116.4, 0.1, "小范围")
        # 约 1km 外
        assert fence.contains(39.91, 116.4) is False

    def test_distance_to_center(self):
        fence = Geofence(39.9, 116.4, 1.0)
        dist = fence.distance_to_center(39.9, 116.4)
        assert dist == 0.0

    def test_to_dict(self):
        fence = Geofence(39.9, 116.4, 0.5, name="仓库区域")
        d = fence.to_dict()
        assert d["name"] == "仓库区域"
        assert d["radius_km"] == 0.5

    def test_create_depot_geofence(self):
        fence = create_depot_geofence(39.9, 116.4)
        assert fence.name == "仓库区域"
        assert fence.radius_km == 0.5

    def test_create_customer_geofence(self):
        fence = create_customer_geofence(39.91, 116.41)
        assert fence.name == "客户点"
        assert fence.radius_km == 0.1
