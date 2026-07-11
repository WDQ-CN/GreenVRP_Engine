"""SolverService 求解结果缓存回归测试。

验证缓存使用 JSON 序列化/反序列化后，调用方修改返回值不会污染缓存，
并在遇到不可序列化类型时能降级为 deepcopy。
"""

from api.services.solver_service import SolverService


def test_solver_cache_returns_isolated_copy():
    """命中缓存后修改返回值不应影响缓存中的原始数据。"""
    service = SolverService()
    result = {
        "solution": {"total_distance": 100.0, "routes": []},
        "cost_result": {"total_cost": 500.0},
    }
    service._set_cached_result("key1", result)

    cached = service._get_cached_result("key1")
    assert cached is not None
    cached["solution"]["total_distance"] = 999.0
    cached["cost_result"]["new_field"] = "pollution"

    cached_again = service._get_cached_result("key1")
    assert cached_again is not None
    assert cached_again["solution"]["total_distance"] == 100.0
    assert "new_field" not in cached_again["cost_result"]


def test_solver_cache_fallback_to_deepcopy_for_non_serializable_result():
    """不可序列化类型（如 set）应触发 deepcopy 降级，且仍保持隔离。"""
    service = SolverService()
    result = {"data": {1, 2, 3}}
    service._set_cached_result("key2", result)

    cached = service._get_cached_result("key2")
    assert cached is not None
    cached["data"].add(4)

    cached_again = service._get_cached_result("key2")
    assert cached_again is not None
    assert cached_again["data"] == {1, 2, 3}
