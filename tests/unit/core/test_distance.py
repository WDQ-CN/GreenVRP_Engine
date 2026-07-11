"""
单元测试：core/distance.py — 距离矩阵
"""

import numpy as np
import pytest
from pytest import approx

from core.distance import (
    DistanceMatrixCache,
    SparseDistanceMatrix,
    build_distance_matrix,
    build_time_matrix,
    build_time_matrix_numpy,
    haversine_vectorized,
)
from exceptions.errors import DistanceCalculationError
from utils.geo import haversine_distance


# =========================================================================
# Haversine (标量)
# =========================================================================

class TestHaversine:
    def test_same_point_zero(self):
        assert haversine_distance(39.9, 116.4, 39.9, 116.4) == approx(0.0)

    def test_known_distance(self):
        # 北京-上海 约 1068 km
        d = haversine_distance(39.9042, 116.4074, 31.2304, 121.4737)
        assert d == approx(1068.0, abs=10)

    def test_symmetry(self):
        d1 = haversine_distance(39.9, 116.4, 31.2, 121.5)
        d2 = haversine_distance(31.2, 121.5, 39.9, 116.4)
        assert d1 == approx(d2)


# =========================================================================
# Haversine Vectorized
# =========================================================================

class TestHaversineVectorized:
    def test_matches_scalar(self):
        lats = np.array([39.9, 31.2])
        lons = np.array([116.4, 121.5])
        vec = haversine_vectorized(lats, lons, lats, lons)
        for i in range(len(lats)):
            for j in range(len(lats)):
                s = haversine_distance(lats[i], lons[i], lats[j], lons[j])
                assert vec[i][j] == approx(s, abs=1e-6)

    def test_single_point(self):
        result = haversine_vectorized(
            np.array([39.9]), np.array([116.4]),
            np.array([39.9]), np.array([116.4]),
        )
        assert result.shape == (1, 1)
        assert result[0][0] == approx(0.0)


# =========================================================================
# Build Distance Matrix
# =========================================================================

class TestBuildDistanceMatrix:
    def test_empty(self):
        assert build_distance_matrix([], 1.0) == []

    def test_single(self):
        assert build_distance_matrix([(39.9, 116.4)], 1.0) == [[0.0]]

    def test_multi_shape(self):
        locs = [(39.9, 116.4), (31.2, 121.5), (40.0, 116.5)]
        m = build_distance_matrix(locs, 1.0)
        assert len(m) == 3 and len(m[0]) == 3
        assert m[0][0] == approx(0.0) and m[1][1] == approx(0.0)

    def test_scale(self):
        locs = [(39.9, 116.4), (31.2, 121.5)]
        km = build_distance_matrix(locs, 1.0)
        m = build_distance_matrix(locs, 1000.0)
        assert m[0][1] == approx(km[0][1] * 1000, rel=1e-3)

    def test_sparse(self):
        locs = [(39.9, 116.4), (31.2, 121.5)]
        result = build_distance_matrix(locs, 1.0, use_sparse=True)
        assert isinstance(result, SparseDistanceMatrix)


# =========================================================================
# Build Time Matrix
# =========================================================================

class TestBuildTimeMatrix:
    def test_empty(self):
        assert build_time_matrix([], 40.0) == []

    def test_zero_distance(self):
        assert build_time_matrix([[0, 0], [0, 0]], 40.0) == [[0, 0], [0, 0]]

    def test_known_time(self):
        # 距离单位：米。40000 m = 40 km, 40 km/h → 60 min
        m = build_time_matrix([[0, 40000], [40000, 0]], 40.0)
        assert m[0][1] == 60

    def test_invalid_speed(self):
        with pytest.raises(DistanceCalculationError):
            build_time_matrix([[0]], 0.0)

    def test_symmetry(self):
        m = build_time_matrix([[0, 40000], [40000, 0]], 40.0)
        assert m[0][1] == m[1][0]


class TestBuildTimeMatrixNumpy:
    def test_numpy_input(self):
        dist = np.array([[0, 40000], [40000, 0]], dtype=np.float64)
        t = build_time_matrix_numpy(dist, 40.0)
        assert t[0][1] == 60

    def test_invalid_speed(self):
        with pytest.raises(DistanceCalculationError):
            build_time_matrix_numpy(np.array([[0.0]]), 0.0)


# =========================================================================
# SparseDistanceMatrix
# =========================================================================

class TestSparseDistanceMatrix:
    def test_get_dense(self):
        locs = [(39.9, 116.4), (31.2, 121.5)]
        sm = SparseDistanceMatrix(locs, max_distance_km=2000)
        dense = sm.to_dense()
        assert len(dense) == 2
        assert dense[0][0] == approx(0.0)
        # 北京-上海 在 2000 km 内，应可连接
        assert dense[0][1] > 0

    def test_get_unconnected(self):
        locs = [(39.9, 116.4), (31.2, 121.5)]
        sm = SparseDistanceMatrix(locs, max_distance_km=100)  # 北京-上海 > 100 km
        assert sm.get(0, 1) == float("inf")

    def test_single_node(self):
        sm = SparseDistanceMatrix([(39.9, 116.4)], max_distance_km=500)
        assert sm.get(0, 0) == 0.0


# =========================================================================
# DistanceMatrixCache
# =========================================================================

class TestDistanceMatrixCache:
    def test_hit(self):
        cache = DistanceMatrixCache()
        locs = [(39.9, 116.4), (31.2, 121.5)]
        m1 = cache.get_or_compute(locs, scale=1000)
        m2 = cache.get_or_compute(locs, scale=1000)
        assert m1 is m2  # same object

    def test_miss(self):
        cache = DistanceMatrixCache()
        m1 = cache.get_or_compute([(39.9, 116.4)], scale=1000)
        m2 = cache.get_or_compute([(31.2, 121.5)], scale=1000)
        assert m1 is not m2

    def test_clear(self):
        cache = DistanceMatrixCache()
        cache.get_or_compute([(39.9, 116.4)], scale=1000)
        cache.clear()
        assert len(cache._cache) == 0

    def test_hash_consistency(self):
        cache = DistanceMatrixCache()
        h1 = cache._hash_locations([(39.9, 116.4)], scale=1000)
        h2 = cache._hash_locations([(39.9, 116.4)], scale=1000)
        assert h1 == h2

    def test_hash_diff_scale(self):
        cache = DistanceMatrixCache()
        h1 = cache._hash_locations([(39.9, 116.4)], scale=1000)
        h2 = cache._hash_locations([(39.9, 116.4)], scale=1)
        assert h1 != h2
