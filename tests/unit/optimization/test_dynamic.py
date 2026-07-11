"""
单元测试：optimization/dynamic.py — 动态重优化
"""

import pytest

from optimization.dynamic import DynamicEvent, DynamicReoptimizer, EventType, ReoptimizationResult
from tests.fixtures.customers import get_minimal_solution


class TestDynamicEvent:
    def test_to_dict(self):
        event = DynamicEvent(
            event_type=EventType.NEW_ORDER,
            data={"customer_id": 10, "lat": 39.9, "lon": 116.4, "demand": 50},
            timestamp=1000.0,
        )
        d = event.to_dict()
        assert d["event_type"] == "new_order"
        assert d["data"]["customer_id"] == 10
        assert d["timestamp"] == 1000.0

    def test_from_dict(self):
        d = {"event_type": "traffic_delay", "data": {"segment": (0, 1), "delay_minutes": 15},
             "timestamp": 2000.0}
        event = DynamicEvent.from_dict(d)
        assert event.event_type == EventType.TRAFFIC_DELAY
        assert event.data["delay_minutes"] == 15
        assert event.timestamp == 2000.0

    def test_round_trip(self):
        original = DynamicEvent(
            event_type=EventType.VEHICLE_BREAKDOWN,
            data={"vehicle_id": 1, "breakdown_time": 500.0},
            timestamp=3000.0,
        )
        restored = DynamicEvent.from_dict(original.to_dict())
        assert restored.event_type == original.event_type
        assert restored.data == original.data
        assert restored.timestamp == original.timestamp


class TestDynamicReoptimizer:
    @pytest.fixture
    def customers(self):
        return [
            {"id": 0, "name": "仓库", "lat": 39.9042, "lon": 116.4074,
             "demand": 0, "service_time_min": 0, "tw_earliest": 480, "tw_latest": 960},
            {"id": 1, "name": "客户A", "lat": 39.9123, "lon": 116.3456,
             "demand": 45, "service_time_min": 15, "tw_earliest": 500, "tw_latest": 600},
        ]

    @pytest.fixture
    def vehicle_config(self):
        return {"4.2m": {"capacity": 800, "fixed_cost": 200,
                          "fuel_per_100km": 12, "speed_kmh": 40, "count": 2}}

    @pytest.fixture
    def params(self):
        return {"fuel_price": 7.5, "hourly_wage": 50.0}

    @pytest.fixture
    def reoptimizer(self, customers, vehicle_config, params):
        def solver_func(customers_df, vehicle_config, params):
            return {"solution": {"routes": [], "total_distance": 0},
                    "cost_result": {"total_cost": 0}}
        return DynamicReoptimizer(solver_func, customers, vehicle_config, params)

    @pytest.fixture
    def reoptimizer_with_solution(self, reoptimizer):
        solution = get_minimal_solution()
        reoptimizer.set_current_solution(solution)
        return reoptimizer

    def test_set_current_solution(self, reoptimizer):
        solution = get_minimal_solution()
        reoptimizer.set_current_solution(solution)
        assert reoptimizer.current_solution is not None
        assert reoptimizer.current_solution["total_distance"] == 10.0

    def test_handle_event_no_solution(self, reoptimizer):
        event = DynamicEvent(event_type=EventType.NEW_ORDER, data={}, timestamp=0)
        result = reoptimizer.handle_event(event)
        assert isinstance(result, ReoptimizationResult)
        assert result.success is False

    def test_handle_new_order_full(self, reoptimizer_with_solution):
        event = DynamicEvent(
            event_type=EventType.NEW_ORDER,
            data={"customer_id": 99, "lat": 39.95, "lon": 116.45,
                  "demand": 30, "service_time_min": 15,
                  "tw_earliest": 500, "tw_latest": 700},
            timestamp=0,
        )
        result = reoptimizer_with_solution.handle_event(event, full_reoptimize=True)
        assert isinstance(result, ReoptimizationResult)
        # 结果可能是 True 或 False（取决于 solver_func 实现），但不应抛出异常

    def test_handle_new_order_missing_data(self, reoptimizer_with_solution):
        event = DynamicEvent(event_type=EventType.NEW_ORDER, data={}, timestamp=0)
        result = reoptimizer_with_solution.handle_event(event)
        assert result.success is False

    def test_handle_cancel_missing_id(self, reoptimizer_with_solution):
        event = DynamicEvent(event_type=EventType.CANCEL_ORDER, data={}, timestamp=0)
        result = reoptimizer_with_solution.handle_event(event)
        assert result.success is False

    def test_handle_traffic_delay_missing_segment(self, reoptimizer_with_solution):
        event = DynamicEvent(event_type=EventType.TRAFFIC_DELAY, data={}, timestamp=0)
        result = reoptimizer_with_solution.handle_event(event)
        assert result.success is False

    def test_handle_vehicle_breakdown(self, reoptimizer_with_solution):
        event = DynamicEvent(
            event_type=EventType.VEHICLE_BREAKDOWN,
            data={"vehicle_id": 999, "breakdown_time": 500.0},
            timestamp=0,
        )
        result = reoptimizer_with_solution.handle_event(event)
        assert isinstance(result, ReoptimizationResult)

    def test_unsupported_event(self, reoptimizer_with_solution):
        event = DynamicEvent(
            event_type=EventType.CUSTOMER_CHANGE,
            data={},
            timestamp=0,
        )
        result = reoptimizer_with_solution.handle_event(event)
        assert result.success is False

    def test_reoptimization_result_to_dict(self):
        result = ReoptimizationResult(
            success=True,
            old_solution={"total_distance": 100},
            new_solution={"total_distance": 90},
            changes=[{"type": "reroute", "vehicle_id": 0}],
            cost_delta=-50.0,
            reoptimization_time=1.5,
            affected_routes=[0],
            message="成功优化",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["cost_delta"] == -50.0
        assert len(d["changes"]) == 1
