"""
单元测试：core/distance.py
"""

import numpy as np
import pytest

from core.distance import (
    DistanceMatrixCache,
    build_distance_matrix,
    build_time_matrix,
    build_time_matrix_numpy,
    haversine_vectorized,
)
from utils.geo import haversine_distance as haversine


class TestHaversine:
    def test_same_point_zero_distance(self):
        assert haversine(39.9, 116.4, 39.9, 116.4) == pytest.approx(0.0, abs=1e-6)

    def test_known_distance_beijing_shanghai(self):
        # 北京 -> 上海 约 1068 km
        dist = haversine(39.9042, 116.4074, 31.2304, 121.4737)
        assert dist == pytest.approx(1068.0, abs=50.0)

    def test_symmetry(self):
        d1 = haversine(39.9, 116.4, 31.2, 121.5)
        d2 = haversine(31.2, 121.5, 39.9, 116.4)
        assert d1 == pytest.approx(d2, abs=1e-6)


class TestHaversineVectorized:
    def test_vectorized_same_as_scalar(self):
        lats = np.array([39.9, 31.2])
        lons = np.array([116.4, 121.5])
        mat = haversine_vectorized(lats, lons, lats, lons)
        assert mat.shape == (2, 2)
        assert mat[0, 0] == pytest.approx(0.0, abs=1e-6)
        assert mat[1, 1] == pytest.approx(0.0, abs=1e-6)
        assert mat[0, 1] == pytest.approx(haversine(39.9, 116.4, 31.2, 121.5), abs=1e-3)


class TestBuildDistanceMatrix:
    def test_empty_locations(self):
        assert build_distance_matrix([]) == []

    def test_single_location(self):
        mat = build_distance_matrix([(39.9, 116.4)])
        assert len(mat) == 1
        assert mat[0][0] == 0

    def test_multiple_locations_shape(self):
        locations = [(39.9, 116.4), (31.2, 121.5), (30.5, 114.3)]
        mat = build_distance_matrix(locations)
        assert len(mat) == 3
        assert all(len(row) == 3 for row in mat)
        assert mat[0][0] == 0
        assert mat[1][1] == 0
        assert mat[0][1] == mat[1][0]

    def test_scale_factor(self):
        # 使用较大距离避免 scale=1 时的整数截断误差
        locations = [(39.9, 116.4), (40.9, 116.4)]
        mat_m = build_distance_matrix(locations, scale=1000)
        mat_km = build_distance_matrix(locations, scale=1)
        assert mat_m[0][1] == pytest.approx(mat_km[0][1] * 1000, rel=2e-3)


class TestBuildTimeMatrix:
    def test_empty_matrix(self):
        assert build_time_matrix([], 40.0) == []

    def test_zero_distance_zero_time(self):
        dist = [[0, 0], [0, 0]]
        time_mat = build_time_matrix(dist, 40.0)
        assert time_mat[0][0] == 0
        assert time_mat[1][1] == 0

    def test_known_time(self):
        # 40 km at 40 km/h -> 60 min
        dist = [[0, 40000], [40000, 0]]
        time_mat = build_time_matrix(dist, 40.0)
        assert time_mat[0][1] == pytest.approx(60, abs=1)

    def test_invalid_speed_raises(self):
        with pytest.raises(ValueError, match="速度必须大于0"):
            build_time_matrix([[0, 1000], [1000, 0]], 0.0)


class TestBuildTimeMatrixNumpy:
    def test_numpy_array_input(self):
        dist = np.array([[0, 40000], [40000, 0]], dtype=np.int32)
        time_mat = build_time_matrix_numpy(dist, 40.0)
        assert isinstance(time_mat, np.ndarray)
        assert time_mat[0, 1] == pytest.approx(60, abs=1)


class TestDistanceMatrixCache:
    def test_cache_hit(self):
        cache = DistanceMatrixCache()
        locations = [(39.9, 116.4), (31.2, 121.5)]
        mat1 = cache.get_or_compute(locations)
        mat2 = cache.get_or_compute(locations)
        assert mat1 is mat2

    def test_cache_miss(self):
        cache = DistanceMatrixCache()
        mat1 = cache.get_or_compute([(39.9, 116.4), (31.2, 121.5)])
        mat2 = cache.get_or_compute([(39.9, 116.4), (31.2, 121.5), (30.5, 114.3)])
        assert mat1 is not mat2

    def test_clear(self):
        cache = DistanceMatrixCache()
        cache.get_or_compute([(39.9, 116.4)])
        assert len(cache._cache) == 1
        cache.clear()
        assert len(cache._cache) == 0
