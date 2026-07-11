"""场景列表缓存回归测试。

验证 _get_cached_scenarios 返回深拷贝，调用方修改不会污染缓存。
"""

from datetime import datetime

from api.routers.scenarios import (
    ScenarioResponse,
    _get_cached_scenarios,
    _set_cached_scenarios,
)


def test_cached_scenarios_returns_deep_copy():
    """缓存读取应返回深拷贝，避免调用方修改影响后续读取。"""
    # 准备缓存数据
    now = datetime(2026, 6, 30, 12, 0, 0)
    original = ScenarioResponse(
        id=1,
        name="原始名称",
        description="原始描述",
        customer_count=2,
        solution_count=0,
        created_at=now,
        updated_at=now,
    )
    _set_cached_scenarios(limit=10, offset=0, value=[original])

    # 第一次读取并修改
    cached = _get_cached_scenarios(limit=10, offset=0)
    assert cached is not None
    cached[0].name = "被修改的名称"

    # 第二次读取应仍为原始数据
    cached_again = _get_cached_scenarios(limit=10, offset=0)
    assert cached_again is not None
    assert cached_again[0].name == "原始名称"

    # 清理缓存，避免影响其他测试
    from api.routers.scenarios import _invalidate_scenarios_cache

    _invalidate_scenarios_cache()
