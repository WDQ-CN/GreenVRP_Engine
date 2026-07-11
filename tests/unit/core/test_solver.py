"""
单元测试：core/solver.py — SolverInstancePool 和 CallbackCache
"""

from unittest.mock import patch

from core.solver import CallbackCache, SolverInstancePool


class TestSolverInstancePool:
    def test_init(self):
        pool = SolverInstancePool(max_size=5)
        assert pool.max_size == 5
        assert len(pool._pool) == 0

    def test_get_or_create(self):
        pool = SolverInstancePool(max_size=5)
        with patch("core.solver.pywrapcp.RoutingIndexManager") as mock_mgr, \
             patch("core.solver.pywrapcp.RoutingModel") as mock_model:
            mock_mgr.return_value = "manager"
            mock_model.return_value = "routing"
            r1 = pool.get_or_create("k1", 10, 3)
            r2 = pool.get_or_create("k1", 10, 3)
            assert r1 == r2  # 内容相同
            # 验证只创建了一次
            assert mock_mgr.call_count == 1

    def test_eviction(self):
        pool = SolverInstancePool(max_size=2)
        with patch("core.solver.pywrapcp.RoutingIndexManager") as mock_mgr, \
             patch("core.solver.pywrapcp.RoutingModel") as mock_model:
            mock_mgr.return_value = "mgr"
            mock_model.return_value = "routing"
            pool.get_or_create("k1", 10, 3)
            pool.get_or_create("k2", 10, 3)
            pool.get_or_create("k3", 10, 3)
            assert len(pool._pool) == 2
            assert "k1" not in pool._pool

    def test_clear(self):
        pool = SolverInstancePool(max_size=5)
        with patch("core.solver.pywrapcp.RoutingIndexManager") as mock_mgr, \
             patch("core.solver.pywrapcp.RoutingModel") as mock_model:
            mock_mgr.return_value = "mgr"
            mock_model.return_value = "routing"
            pool.get_or_create("k1", 10, 3)
            pool.clear()
            assert len(pool._pool) == 0


class TestCallbackCache:
    def test_get_or_create(self):
        cache = CallbackCache()
        fn = lambda: "result"
        r1 = cache.get_or_create("t1", fn)
        r2 = cache.get_or_create("t1", fn)
        assert r1 is r2

    def test_clear(self):
        cache = CallbackCache()
        cache.get_or_create("t1", lambda: 1)
        cache.clear()
        assert len(cache._cache) == 0
