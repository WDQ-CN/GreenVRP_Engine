"""Tests for the ALNS post-optimizer."""

from __future__ import annotations

from utils.geo import haversine_distance
from core.cost import calculate_green_cost
from optimization.alns import (
    _build_vehicle_pool,
    _extract_initial,
    improve_solution_with_alns,
)
from tests.fixtures.customers import (
    get_single_type_vehicle_config,
    get_test_params,
    get_test_vehicle_config,
)


def _stop(customer_id, name, lat, lon, demand=0, service_time=0):
    return {
        "node": customer_id or 0,
        "customer_id": customer_id,
        "customer_name": name,
        "lat": lat,
        "lon": lon,
        "demand": demand,
        "service_time": service_time,
        "tw_earliest": 480,
        "tw_latest": 960,
        "arrival_time": 480,
        "departure_time": 480,
        "late_minutes": 0,
        "is_late": False,
    }


def _route(vehicle_id, customers):
    depot = _stop(0, "仓", 39.90, 116.40)
    route_stops = [depot, *customers, _stop(None, "仓·返程", 39.90, 116.40)]
    distance = 0.0
    for left, right in zip(route_stops, route_stops[1:]):
        distance += haversine_distance(
            left["lat"], left["lon"], right["lat"], right["lon"]
        )
    return {
        "vehicle_id": vehicle_id,
        "vehicle_type": "4.2m",
        "vehicle_color": "#84cc16",
        "capacity": 800,
        "stops": route_stops,
        "distance_km": round(distance, 2),
        "total_demand": sum(customer["demand"] for customer in customers),
        "total_time_min": 120,
        "late_minutes": 0,
    }


def _initial_solution():
    a = _stop(1, "A", 39.90, 116.50, 50, 10)
    b = _stop(2, "B", 39.90, 116.30, 50, 10)
    c = _stop(3, "C", 39.95, 116.40, 50, 10)
    d = _stop(4, "D", 39.85, 116.40, 50, 10)
    routes = [_route(0, [a, b]), _route(1, [c, d])]
    return {
        "routes": routes,
        "total_distance": round(sum(route["distance_km"] for route in routes), 2),
        "vehicles_used": {"4.2m": 2},
        "total_late_minutes": 0,
        "solution_status": "SUCCESS",
        "solve_time_seconds": 0.1,
    }


def test_alns_preserves_customers_capacity_and_shape():
    config = get_test_vehicle_config()
    params = get_test_params()
    initial = _initial_solution()
    improved = improve_solution_with_alns(
        initial, config, params, time_limit=0.5, seed=7
    )

    assert improved["solution_status"] == "SUCCESS"
    assert improved["routes"]

    customer_ids = set()
    for route in improved["routes"]:
        customer_stops = [
            stop
            for stop in route["stops"]
            if stop.get("customer_id") not in (0, None)
        ]
        customer_ids.update(int(stop["customer_id"]) for stop in customer_stops)
        assert route["total_demand"] <= route["capacity"]
        assert route["stops"][0]["customer_id"] == 0
        assert route["stops"][-1]["customer_id"] is None
        assert "arrival_time" in route["stops"][-1]
    assert customer_ids == {1, 2, 3, 4}


def test_alns_does_not_worsen_actual_cost():
    config = get_test_vehicle_config()
    params = get_test_params()
    initial = _initial_solution()
    initial_cost = calculate_green_cost(initial, config, params)["total_cost"]

    improved = improve_solution_with_alns(
        initial, config, params, time_limit=1.0, seed=7
    )
    improved_cost = calculate_green_cost(improved, config, params)["total_cost"]

    assert improved_cost <= initial_cost + 1e-6


def test_alns_optimizes_departure_time_for_late_window():
    """客户时间窗较晚时，应推迟出发以避免长时间等待和早高峰。"""
    config = get_test_vehicle_config()
    params = get_test_params()
    customer = _stop(1, "晚窗客户", 39.90, 116.50, 50, 10)
    customer["tw_earliest"] = 700
    customer["tw_latest"] = 900
    initial = {
        "routes": [_route(0, [customer])],
        "total_distance": 20.0,
        "vehicles_used": {"4.2m": 1},
        "total_late_minutes": 0,
        "solution_status": "SUCCESS",
        "solve_time_seconds": 0.1,
    }

    improved = improve_solution_with_alns(
        initial, config, params, time_limit=0.8, seed=3
    )

    route = improved["routes"][0]
    assert route["stops"][0]["arrival_time"] > 600
    assert route["stops"][1]["arrival_time"] >= 700
    initial_cost = calculate_green_cost(initial, config, params)["total_cost"]
    improved_cost = calculate_green_cost(improved, config, params)["total_cost"]
    assert improved_cost <= initial_cost + 1e-6


def test_extract_initial_reassigns_duplicate_vehicle_ids():
    """重复车辆 ID 应被重新分配到同类型空闲车辆。"""
    solution = _initial_solution()
    solution["routes"][1]["vehicle_id"] = solution["routes"][0]["vehicle_id"]

    pool = _build_vehicle_pool(get_test_vehicle_config())
    routes, available, depot = _extract_initial(solution, pool)

    assert routes is not None and depot is not None
    vehicle_ids = {route.vehicle.vehicle_id for route in routes}
    assert len(vehicle_ids) == len(routes)


def test_extract_initial_matches_vehicle_type_not_just_id():
    """车辆 ID 命中的车型与路线不一致时，应改配同车型空闲车辆。"""
    solution = _initial_solution()
    solution["routes"][0]["vehicle_type"] = "7.6m"

    pool = _build_vehicle_pool(get_test_vehicle_config())
    routes, available, depot = _extract_initial(solution, pool)

    assert routes is not None and depot is not None
    assert routes[0].vehicle.vehicle_type == "7.6m"
    assert routes[0].vehicle.vehicle_id != solution["routes"][0]["vehicle_id"]
    assert routes[1].vehicle.vehicle_type == "4.2m"


def test_extract_initial_rejects_solution_exceeding_fleet():
    """超出车队数量时拒绝提取，交由上层回退。"""
    solution = _initial_solution()
    config = get_single_type_vehicle_config()
    config["4.2m"]["count"] = 1

    pool = _build_vehicle_pool(config)
    routes, available, depot = _extract_initial(solution, pool)

    assert routes is None and available is None and depot is None


def test_alns_returns_original_for_empty_or_failed_solution():
    config = get_test_vehicle_config()
    params = get_test_params()
    empty = {"routes": [], "solution_status": "NO_SOLUTION_FOUND"}
    assert improve_solution_with_alns(empty, config, params) is empty

    failed = {"routes": [], "solution_status": "SUCCESS"}
    assert improve_solution_with_alns(failed, config, params) is failed
