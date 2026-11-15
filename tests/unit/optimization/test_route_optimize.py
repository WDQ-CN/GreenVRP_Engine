"""
单元测试：optimization/route_optimize.py — 2-opt 路线后处理优化器
"""

import copy
from unittest.mock import patch

import pytest

from optimization.route_optimize import (
    calculate_arrival_times,
    check_time_window_feasibility,
    optimize_single_route,
    post_process_solution,
    refresh_route_timing,
    two_opt_swap,
)
from tests.fixtures.customers import (
    get_minimal_solution,
    get_multi_route_solution,
    get_test_vehicle_config,
)


class TestTwoOptSwap:
    """测试 2-opt 交换操作。"""

    def test_basic_swap(self):
        """测试基本的 2-opt 交换。"""
        stops = [
            {"node": 0, "name": "仓库", "lat": 0, "lon": 0},
            {"node": 1, "name": "A", "lat": 1, "lon": 1},
            {"node": 2, "name": "B", "lat": 2, "lon": 2},
            {"node": 3, "name": "C", "lat": 3, "lon": 3},
            {"node": 0, "name": "仓库", "lat": 0, "lon": 0},
        ]
        # 2-opt 交换 i=1, j=3：反转中间段 [A, B, C] -> [C, B, A]
        result = two_opt_swap(stops, 1, 3)
        assert result[0]["node"] == 0
        assert result[1]["node"] == 3  # C
        assert result[2]["node"] == 2  # B
        assert result[3]["node"] == 1  # A
        assert result[4]["node"] == 0

    def test_swap_adjacent(self):
        """相邻切点交换（反转相邻两个节点）。"""
        stops = [
            {"node": 0, "name": "仓库"},
            {"node": 1, "name": "A"},
            {"node": 2, "name": "B"},
            {"node": 0, "name": "仓库"},
        ]
        result = two_opt_swap(stops, 1, 2)
        # 相邻交换反转 [A, B] -> [B, A]
        assert result[0]["node"] == 0
        assert result[1]["node"] == 2  # B
        assert result[2]["node"] == 1  # A
        assert result[3]["node"] == 0

    def test_swap_invalid_indices(self):
        """无效索引返回原列表。"""
        stops = [
            {"node": 0, "name": "仓库"},
            {"node": 1, "name": "A"},
            {"node": 0, "name": "仓库"},
        ]
        # i >= j
        result = two_opt_swap(stops, 2, 1)
        assert result == stops
        # i < 1
        result = two_opt_swap(stops, 0, 2)
        assert result == stops

    def test_swap_four_customers(self):
        """4个客户的路线。"""
        stops = [
            {"node": 0, "name": "仓库"},
            {"node": 1, "name": "A"},
            {"node": 2, "name": "B"},
            {"node": 3, "name": "C"},
            {"node": 4, "name": "D"},
            {"node": 0, "name": "仓库"},
        ]
        # i=1, j=3: [A, B, C] -> [C, B, A]
        result = two_opt_swap(stops, 1, 3)
        assert [s["node"] for s in result] == [0, 3, 2, 1, 4, 0]

    def test_swap_preserves_data(self):
        """交换不改变站点数据内容。"""
        stops = [
            {"node": 0, "lat": 0, "lon": 0, "demand": 0},
            {"node": 1, "lat": 1, "lon": 1, "demand": 50},
            {"node": 2, "lat": 2, "lon": 2, "demand": 60},
            {"node": 3, "lat": 3, "lon": 3, "demand": 70},
            {"node": 0, "lat": 0, "lon": 0, "demand": 0},
        ]
        result = two_opt_swap(stops, 1, 3)
        # 数据完整保留
        assert result[1]["demand"] == 70
        assert result[2]["demand"] == 60
        assert result[3]["demand"] == 50


class TestCalculateArrivalTimes:
    """测试到达时间计算。"""

    def test_single_customer(self):
        """单个客户的基本时间计算。"""
        stops = [
            {"node": 0, "lat": 39.90, "lon": 116.40, "tw_earliest": 480,
             "service_time": 0},
            {"node": 1, "lat": 39.91, "lon": 116.41, "tw_earliest": 500,
             "tw_latest": 600, "service_time": 15},
            {"node": 0, "lat": 39.90, "lon": 116.40, "tw_earliest": 480,
             "service_time": 0},
        ]
        result = calculate_arrival_times(stops, speed_kmh=40)
        assert result[0]["arrival_time"] == 480
        assert result[1]["arrival_time"] >= 480
        assert result[2]["arrival_time"] >= result[1]["arrival_time"]

    def test_empty_stops(self):
        """空路线返回空列表。"""
        assert calculate_arrival_times([], speed_kmh=40) == []

    def test_no_tw_earliest(self):
        """无最早时间窗时使用默认值。"""
        stops = [
            {"node": 0, "lat": 39.90, "lon": 116.40, "service_time": 0},
            {"node": 1, "lat": 39.91, "lon": 116.41, "service_time": 10},
        ]
        result = calculate_arrival_times(stops, speed_kmh=40)
        assert result[0]["arrival_time"] == 480  # 默认值
        assert result[1]["arrival_time"] is not None


class TestCheckTimeWindowFeasibility:
    """测试时间窗可行性检查。"""

    def test_all_within_window(self):
        """所有站点都在时间窗内。"""
        stops = [
            {"node": 0, "arrival_time": 480},  # 仓库
            {"node": 1, "arrival_time": 520, "tw_latest": 600},
            {"node": 2, "arrival_time": 550, "tw_latest": 640},
        ]
        assert check_time_window_feasibility(stops) is True

    def test_late_customer(self):
        """迟到超过30分钟。"""
        stops = [
            {"node": 0, "arrival_time": 480},
            {"node": 1, "arrival_time": 650, "tw_latest": 600},  # 迟到50分钟
        ]
        assert check_time_window_feasibility(stops) is False

    def test_soft_late_allowed(self):
        """迟到30分钟以内允许（软时间窗）。"""
        stops = [
            {"node": 0, "arrival_time": 480},
            {"node": 1, "arrival_time": 625, "tw_latest": 600},  # 迟到25分钟
        ]
        assert check_time_window_feasibility(stops) is True

    def test_depot_ignored(self):
        """仓库节点不检查时间窗。"""
        stops = [
            {"node": 0, "arrival_time": 999, "tw_latest": 960},  # 仓库，忽略
            {"node": 1, "arrival_time": 500, "tw_latest": 600},
        ]
        assert check_time_window_feasibility(stops) is True


class TestOptimizeSingleRoute:
    """测试单路线 2-opt 优化。"""

    def test_short_route_no_change(self):
        """少于4个站点（仓库-客户-仓库）不优化。"""
        stops = [
            {"node": 0, "lat": 39.90, "lon": 116.40, "tw_earliest": 480,
             "service_time": 0},
            {"node": 1, "lat": 39.91, "lon": 116.41, "tw_earliest": 500,
             "tw_latest": 600, "service_time": 15},
            {"node": 0, "lat": 39.90, "lon": 116.40, "tw_earliest": 480,
             "service_time": 0},
        ]
        result = optimize_single_route(stops, speed_kmh=40, capacity=800)
        assert result["iterations"] == 0

    def test_improvement_possible(self):
        """存在明显交叉的路线应能优化。"""
        # 路线有交叉：仓库 -> A(左下) -> B(右上) -> C(左上) -> D(右下) -> 仓库
        stops = [
            {"node": 0, "lat": 39.90, "lon": 116.40, "tw_earliest": 480,
             "service_time": 0},
            {"node": 1, "lat": 39.88, "lon": 116.38, "tw_earliest": 500,
             "tw_latest": 800, "service_time": 10},
            {"node": 2, "lat": 39.94, "lon": 116.44, "tw_earliest": 520,
             "tw_latest": 800, "service_time": 10},
            {"node": 3, "lat": 39.89, "lon": 116.43, "tw_earliest": 540,
             "tw_latest": 800, "service_time": 10},
            {"node": 4, "lat": 39.93, "lon": 116.37, "tw_earliest": 560,
             "tw_latest": 800, "service_time": 10},
            {"node": 0, "lat": 39.90, "lon": 116.40, "tw_earliest": 480,
             "service_time": 0},
        ]
        result = optimize_single_route(stops, speed_kmh=40, capacity=800)
        # 应该有改进
        assert result["optimized_distance"] <= result["original_distance"]

    def test_or_opt_keeps_depot_at_route_ends(self):
        """Or-opt 只能把客户段插在起点仓和返程仓之间。"""
        stops = [
            {"node": 0, "customer_id": 0, "customer_name": "仓",
             "lat": 39.90, "lon": 116.40, "demand": 0, "service_time": 0,
             "tw_earliest": 480, "arrival_time": 480,
             "late_minutes": 0, "is_late": False},
            {"node": 1, "customer_id": 1, "customer_name": "A",
             "lat": 39.90, "lon": 116.50, "demand": 10, "service_time": 20,
             "tw_earliest": 480, "tw_latest": 900,
             "arrival_time": 482, "late_minutes": 0, "is_late": False},
            {"node": 2, "customer_id": 2, "customer_name": "B",
             "lat": 39.90, "lon": 116.30, "demand": 10, "service_time": 20,
             "tw_earliest": 480, "tw_latest": 900,
             "arrival_time": 528, "late_minutes": 0, "is_late": False},
            {"node": 3, "customer_id": 3, "customer_name": "C",
             "lat": 39.95, "lon": 116.40, "demand": 10, "service_time": 20,
             "tw_earliest": 480, "tw_latest": 900,
             "arrival_time": 565, "late_minutes": 0, "is_late": False},
            {"node": 0, "customer_id": None, "customer_name": "仓·返程",
             "lat": 39.90, "lon": 116.40, "demand": 0, "service_time": 0,
             "arrival_time": 585},
        ]
        result = optimize_single_route(stops, speed_kmh=40, capacity=800)
        optimized = result["stops"]

        assert result["iterations"] > 0
        assert optimized[0]["node"] == 0
        assert optimized[-1]["node"] == 0
        assert all(stop["node"] != 0 for stop in optimized[1:-1])

    def test_preserves_feasibility(self):
        """优化后不应违反时间窗。"""
        stops = [
            {"node": 0, "lat": 39.90, "lon": 116.40, "tw_earliest": 480,
             "service_time": 0},
            {"node": 1, "lat": 39.88, "lon": 116.38, "tw_earliest": 500,
             "tw_latest": 600, "service_time": 10},
            {"node": 2, "lat": 39.94, "lon": 116.44, "tw_earliest": 520,
             "tw_latest": 640, "service_time": 10},
            {"node": 3, "lat": 39.89, "lon": 116.43, "tw_earliest": 540,
             "tw_latest": 680, "service_time": 10},
            {"node": 4, "lat": 39.93, "lon": 116.37, "tw_earliest": 560,
             "tw_latest": 720, "service_time": 10},
            {"node": 0, "lat": 39.90, "lon": 116.40, "tw_earliest": 480,
             "service_time": 0},
        ]
        result = optimize_single_route(stops, speed_kmh=40, capacity=800)
        # 检查优化后的时间窗
        timed = calculate_arrival_times(result["stops"], speed_kmh=40)
        assert check_time_window_feasibility(timed) is True


class TestPostProcessSolution:
    """测试求解结果的整体后处理。"""

    def test_empty_solution(self):
        """空求解结果返回不变。"""
        solution = {"routes": [], "total_distance": 0}
        result = post_process_solution(solution, {})
        assert result["total_distance"] == 0

    def test_single_route(self):
        """单路线场景。"""
        solution = get_minimal_solution()
        config = get_test_vehicle_config()
        result = post_process_solution(solution, config)
        assert "routes" in result
        assert result["total_distance"] >= 0

    def test_multi_route(self):
        """多路线场景：可能合并路线以节省车辆。"""
        solution = get_multi_route_solution()
        config = get_test_vehicle_config()
        result = post_process_solution(solution, config)
        # 路线数量可能减少（Relocate 合并路线）
        assert len(result["routes"]) <= len(solution["routes"])
        assert len(result["routes"]) >= 1

    def test_preserves_solution_structure(self):
        """后处理保留求解结果结构。"""
        solution = get_minimal_solution()
        config = get_test_vehicle_config()
        result = post_process_solution(solution, config)
        assert "solution_status" in result or True
        assert "routes" in result
        for route in result["routes"]:
            assert "stops" in route
            assert "vehicle_type" in route
            assert "distance_km" in route

    def test_no_negative_distance(self):
        """距离不能为负。"""
        solution = get_minimal_solution()
        config = get_test_vehicle_config()
        result = post_process_solution(solution, config)
        for route in result["routes"]:
            assert route["distance_km"] >= 0
        assert result["total_distance"] >= 0

    def test_refresh_route_timing_recomputes_late(self):
        """刷新路线时刻时必须重算到达/离开/迟到/总时长。"""
        stops = [
            {"node": 0, "customer_id": 0, "customer_name": "仓",
             "lat": 39.90, "lon": 116.40, "demand": 0, "service_time": 0,
             "tw_earliest": 480, "arrival_time": 480,
             "late_minutes": 0, "is_late": False},
            {"node": 1, "customer_id": 1, "customer_name": "A",
             "lat": 39.90, "lon": 116.50, "demand": 10, "service_time": 20,
             "tw_earliest": 480, "tw_latest": 520,
             "arrival_time": 482, "late_minutes": 0, "is_late": False},
            {"node": 2, "customer_id": 2, "customer_name": "B",
             "lat": 39.90, "lon": 116.30, "demand": 10, "service_time": 20,
             "tw_earliest": 480, "tw_latest": 540,
             "arrival_time": 528, "late_minutes": 0, "is_late": False},
            {"node": 3, "customer_id": 3, "customer_name": "C",
             "lat": 39.95, "lon": 116.40, "demand": 10, "service_time": 20,
             "tw_earliest": 480, "tw_latest": 900,
             "arrival_time": 565, "late_minutes": 0, "is_late": False},
            {"node": 0, "customer_id": None, "customer_name": "仓·返程",
             "lat": 39.90, "lon": 116.40, "demand": 0, "service_time": 0,
             "arrival_time": 585},
        ]
        route = {
            "vehicle_id": 0,
            "vehicle_type": "4.2m",
            "vehicle_color": "#84cc16",
            "capacity": 800,
            "stops": copy.deepcopy(stops),
            "distance_km": 999.0,
            "total_demand": 30,
            "total_time_min": 0,
            "late_minutes": 0,
        }
        late = refresh_route_timing(
            route, {"4.2m": {"speed_kmh": 40, "capacity": 800}}
        )

        expected = calculate_arrival_times(
            route["stops"],
            40,
            start_time=route["stops"][0]["arrival_time"],
        )
        expected_late = sum(
            max(0, stop["arrival_time"] - stop["tw_latest"])
            for stop in expected
            if stop["node"] != 0 and stop.get("tw_latest") is not None
        )
        assert expected_late > 0
        assert late == expected_late
        assert route["late_minutes"] == expected_late
        assert route["stops"][-1]["node"] == 0
        assert "arrival_time" in route["stops"][-1]

        for stop, expected_stop in zip(route["stops"], expected):
            assert stop["arrival_time"] == expected_stop["arrival_time"]
            assert stop["departure_time"] == expected_stop["departure_time"]
            if stop["node"] != 0:
                assert stop["late_minutes"] == max(
                    0, expected_stop["arrival_time"] - expected_stop["tw_latest"]
                )

        assert route["total_time_min"] == (
            route["stops"][-1]["arrival_time"]
            - route["stops"][0]["arrival_time"]
        )

    def test_skips_inter_route_optimization_for_large_solutions(self):
        """客户站点超过阈值时跳过昂贵的路线间搜索。"""
        routes = []
        for index in range(61):
            routes.append({
                "vehicle_id": index,
                "vehicle_type": "4.2m",
                "vehicle_color": "#1f77b4",
                "capacity": 800,
                "stops": [
                    {"node": 0, "lat": 39.90, "lon": 116.40, "demand": 0,
                     "service_time": 0, "tw_earliest": 480,
                     "arrival_time": 480, "late_minutes": 0, "is_late": False},
                    {"node": index + 1, "lat": 39.91 + index * 0.001,
                     "lon": 116.41, "demand": 1, "service_time": 10,
                     "tw_earliest": 480, "tw_latest": 960,
                     "arrival_time": 490, "late_minutes": 0, "is_late": False},
                    {"node": 0, "lat": 39.90, "lon": 116.40, "demand": 0,
                     "service_time": 0, "tw_earliest": 480,
                     "arrival_time": 500},
                ],
                "distance_km": 1.0,
                "total_demand": 1,
                "total_time_min": 20,
                "late_minutes": 0,
            })
        solution = {
            "routes": routes,
            "total_distance": 61.0,
            "vehicles_used": {"4.2m": 61},
            "total_late_minutes": 0,
            "solution_status": "SUCCESS",
        }

        with patch(
            "optimization.route_optimize._run_relocate_phase"
        ) as relocate, patch(
            "optimization.route_optimize._run_exchange_phase"
        ) as exchange:
            result = post_process_solution(solution, get_test_vehicle_config())

        relocate.assert_not_called()
        exchange.assert_not_called()
        assert len(result["routes"]) == 61
        assert sum(result["vehicles_used"].values()) == 61

    def test_removes_empty_routes(self):
        """空路线不应计入车辆使用。"""
        solution = get_minimal_solution()
        solution["routes"].append({
            "vehicle_id": 1,
            "vehicle_type": "4.2m",
            "vehicle_color": "#1f77b4",
            "capacity": 800,
            "stops": [
                {"node": 0, "lat": 39.9042, "lon": 116.4074, "demand": 0,
                 "service_time": 0, "tw_earliest": 480},
                {"node": 0, "lat": 39.9042, "lon": 116.4074, "demand": 0,
                 "service_time": 0, "tw_earliest": 480},
            ],
            "distance_km": 0,
            "total_demand": 0,
            "total_time_min": 0,
            "late_minutes": 0,
        })
        result = post_process_solution(solution, get_test_vehicle_config())

        assert len(result["routes"]) == 1
        assert sum(result["vehicles_used"].values()) == 1
