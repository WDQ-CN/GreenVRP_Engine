"""
单元测试：utils/geo.py — 地理计算工具函数
"""

import pytest
from pytest import approx

from utils.geo import (
    calculate_bearing,
    destination_point,
    haversine_distance,
    point_in_circle,
    point_in_polygon,
)


class TestHaversineDistance:
    def test_same_point(self):
        assert haversine_distance(39.9, 116.4, 39.9, 116.4) == approx(0.0)

    def test_beijing_shanghai(self):
        d = haversine_distance(39.9042, 116.4074, 31.2304, 121.4737)
        assert d == approx(1068.0, abs=10)

    def test_symmetry(self):
        d1 = haversine_distance(39.9, 116.4, 31.2, 121.5)
        d2 = haversine_distance(31.2, 121.5, 39.9, 116.4)
        assert d1 == approx(d2)


class TestCalculateBearing:
    def test_north(self):
        bearing = calculate_bearing(39.9, 116.4, 40.9, 116.4)
        assert bearing == approx(0.0, abs=1)

    def test_south(self):
        bearing = calculate_bearing(40.0, 116.4, 39.0, 116.4)
        assert bearing == approx(180.0, abs=1)

    def test_east(self):
        bearing = calculate_bearing(39.9, 116.4, 39.9, 117.4)
        assert bearing == approx(90.0, abs=1)

    def test_normalized_range(self):
        bearing = calculate_bearing(39.9, 116.4, 39.9, 116.5)
        assert 0 <= bearing <= 360


class TestDestinationPoint:
    def test_basic(self):
        lat, lon = destination_point(39.9, 116.4, 0, 111.0)
        # 向北111km ≈ 1度纬度
        assert lat == approx(40.9, abs=0.5)
        assert lon == approx(116.4, abs=0.5)

    def test_zero_distance(self):
        lat, lon = destination_point(39.9, 116.4, 90, 0)
        assert lat == approx(39.9)
        assert lon == approx(116.4)


class TestPointInCircle:
    def test_inside(self):
        assert point_in_circle(39.91, 116.41, 39.9, 116.4, 10.0) is True

    def test_outside(self):
        assert point_in_circle(40.0, 116.5, 39.9, 116.4, 5.0) is False

    def test_at_center(self):
        assert point_in_circle(39.9, 116.4, 39.9, 116.4, 1.0) is True


class TestPointInPolygon:
    def test_inside(self):
        polygon = [(39.9, 116.4), (40.0, 116.4), (40.0, 116.5), (39.9, 116.5)]
        assert point_in_polygon(39.95, 116.45, polygon) is True

    def test_outside(self):
        polygon = [(39.9, 116.4), (40.0, 116.4), (40.0, 116.5), (39.9, 116.5)]
        assert point_in_polygon(41.0, 117.0, polygon) is False

    def test_less_than_three_vertices(self):
        assert point_in_polygon(39.9, 116.4, [(39.9, 116.4), (40.0, 116.4)]) is False

    def test_on_vertex(self):
        polygon = [(39.9, 116.4), (40.0, 116.4), (40.0, 116.5), (39.9, 116.5)]
        assert point_in_polygon(39.9, 116.4, polygon) is True
