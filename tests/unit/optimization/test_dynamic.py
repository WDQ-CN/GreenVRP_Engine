"""
单元测试：optimization/dynamic.py
"""

import time

import pytest

from optimization.dynamic import (
    DynamicEvent,
    DynamicReoptimizer,
    EventType,
    ReoptimizationResult,
)
from tests.fixtures.customers import (
    get_minimal_solution,
    get_test_customers_df,
    get_test_params,
    get_test_vehicle_config,
)


def dummy_solver(customers_df, vehicle_config, params):
    """旧签名伪求解函数。"""
    return get_minimal_solution()


@pytest.fixture
def reoptimizer():
    customers = get_test_customers_df().to_dict("records")
    return DynamicReoptimizer(
        dummy_solver,
        customers,
        get_test_vehicle_config(),
        get_test_params(),
    )


@pytest.fixture
def reoptimizer_with_solution(reoptimizer):
    reoptimizer.set_current_solution(get_minimal_solution())
    return reoptimizer


class TestDynamicEvent:
    def test_to_dict(self):
        event = DynamicEvent(
            event_type=EventType.NEW_ORDER,
            timestamp=time.time(),
            data={"customer": {"id": 99}},
        )
        d = event.to_dict()
        assert d["event_type"] == "new_order"
        assert "timestamp" in d

    def test_from_dict(self):
        d = {
            "event_type": "cancel_order",
            "timestamp": 1234567890.0,
            "data": {"customer_id": 5},
        }
        event = DynamicEvent.from_dict(d)
        assert event.event_type == EventType.CANCEL_ORDER
        assert event.data["customer_id"] == 5


class TestDynamicReoptimizer:
    def test_set_current_solution(self, reoptimizer):
        sol = get_minimal_solution()
        reoptimizer.set_current_solution(sol)
        assert reoptimizer.current_solution is sol

    def test_handle_event_no_solution(self, reoptimizer):
        event = DynamicEvent(
            event_type=EventType.NEW_ORDER,
            timestamp=time.time(),
            data={"customer": {"id": 99, "lat": 39.9, "lon": 116.4}},
        )
        result = reoptimizer.handle_event(event)
        assert isinstance(result, ReoptimizationResult)
        assert not result.success
        assert "无可用的当前解" in result.message

    def test_handle_new_order_full_reoptimize(self, reoptimizer_with_solution):
        event = DynamicEvent(
            event_type=EventType.NEW_ORDER,
            timestamp=time.time(),
            data={"customer": {"id": 99, "lat": 39.9, "lon": 116.4, "demand": 10}},
        )
        result = reoptimizer_with_solution.handle_event(event, full_reoptimize=True)
        assert isinstance(result, ReoptimizationResult)
        # full_reoptimize 会调用 dummy_solver，应该成功
        assert result.success

    def test_handle_cancel_order_missing_id(self, reoptimizer_with_solution):
        event = DynamicEvent(
            event_type=EventType.CANCEL_ORDER,
            timestamp=time.time(),
            data={},
        )
        result = reoptimizer_with_solution.handle_event(event)
        assert not result.success
        assert "缺少客户ID" in result.message

    def test_handle_traffic_delay_missing_segment(self, reoptimizer_with_solution):
        event = DynamicEvent(
            event_type=EventType.TRAFFIC_DELAY,
            timestamp=time.time(),
            data={"delay_minutes": 30},
        )
        result = reoptimizer_with_solution.handle_event(event)
        assert not result.success
        assert "缺少延误路段信息" in result.message

    def test_handle_vehicle_breakdown(self, reoptimizer_with_solution):
        event = DynamicEvent(
            event_type=EventType.VEHICLE_BREAKDOWN,
            timestamp=time.time(),
            data={"vehicle_id": 0},
        )
        result = reoptimizer_with_solution.handle_event(event)
        assert isinstance(result, ReoptimizationResult)
        # 即使成功也可能是触发 full_reoptimize
        assert result.message is not None

    def test_handle_unsupported_event(self, reoptimizer_with_solution):
        class FakeEventType:
            value = "unsupported"

        event = DynamicEvent(
            event_type=FakeEventType(),
            timestamp=time.time(),
            data={},
        )
        result = reoptimizer_with_solution.handle_event(event)
        assert not result.success
        assert "不支持的事件类型" in result.message
