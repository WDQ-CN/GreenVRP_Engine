"""Experiment: re-optimize each route pair with a small OR-Tools model."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.constants import DEFAULT_PARAMS
from core.cost import calculate_green_cost
from core.solver import GreenVRPSolver
from optimization.alns import (
    RouteState,
    _ALNSOptimizer,
    _build_solution,
    _build_vehicle_pool,
    _extract_initial,
)
from ortools.constraint_solver import routing_enums_pb2

ARTIFACTS = Path(__file__).parent / "benchmark_artifacts"
CONFIG: Dict[str, Dict[str, Any]] = {
    "4.2m": {
        "capacity": 800,
        "fixed_cost": 200,
        "fuel_per_100km": 12,
        "speed_kmh": 40,
        "count": 5,
        "color": "#1f77b4",
    },
    "7.6m": {
        "capacity": 1500,
        "fixed_cost": 350,
        "fuel_per_100km": 18,
        "speed_kmh": 35,
        "count": 1,
        "color": "#2ca02c",
    },
}


def _load(name: str) -> Dict[str, Any]:
    with (ARTIFACTS / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _pair_config(route_a: RouteState, route_b: RouteState) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for route in (route_a, route_b):
        counts[route.vehicle.vehicle_type] = (
            counts.get(route.vehicle.vehicle_type, 0) + 1
        )
    config = {}
    for vehicle_type, count in counts.items():
        config[vehicle_type] = {
            **CONFIG[vehicle_type],
            "count": count,
        }
    return config


def _subset_df(
    customers: List[Dict[str, Any]], depot: Dict[str, Any]
) -> pd.DataFrame:
    rows = [
        {
            "id": 0,
            "name": depot.get("customer_name", "仓库"),
            "lat": depot["lat"],
            "lon": depot["lon"],
            "demand": 0,
            "service_time_min": 0,
            "tw_earliest": 480,
            "tw_latest": 1080,
        }
    ]
    for customer in customers:
        rows.append(
            {
                "id": int(customer["customer_id"]),
                "name": customer.get("customer_name", ""),
                "lat": float(customer["lat"]),
                "lon": float(customer["lon"]),
                "demand": float(customer.get("demand", 0) or 0),
                "service_time_min": float(
                    customer.get("service_time", 0) or 0
                ),
                "tw_earliest": int(customer.get("tw_earliest", 480) or 480),
                "tw_latest": int(customer.get("tw_latest", 1080) or 1080),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    solution_name = sys.argv[1] if len(sys.argv) > 1 else "full_t30_v32_sol.json"
    base = _load(solution_name)
    params = {**DEFAULT_PARAMS, "late_penalty_per_min": 10.0}
    pool = _build_vehicle_pool(CONFIG)
    routes, available, depot = _extract_initial(base, pool)
    assert routes is not None and available is not None and depot is not None
    optimizer = _ALNSOptimizer(routes, available, depot, CONFIG, params, 0)
    optimizer.optimize_start_times(optimizer.routes)
    before = calculate_green_cost(base, CONFIG, params)["total_cost"]
    print(f"{solution_name}: actual {before:.2f}, routes {len(routes)}")

    accepted = 0
    for a_index in range(len(routes)):
        if not routes[a_index].customers:
            continue
        for b_index in range(a_index + 1, len(routes)):
            if not routes[b_index].customers:
                continue
            route_a = routes[a_index]
            route_b = routes[b_index]
            customers = list(route_a.customers) + list(route_b.customers)
            subset = _subset_df(customers, depot)
            pair_config = _pair_config(route_a, route_b)
            solver = GreenVRPSolver(
                customers_df=subset,
                vehicle_config=pair_config,
                search_time_limit=3,
            )
            result = solver.solve_with_params(
                first_solution_strategy=(
                    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
                ),
                metaheuristic=(
                    routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
                ),
                time_limit=3,
            )
            if (
                result.get("solution_status") != "SUCCESS"
                or not result.get("routes")
            ):
                continue
            new_routes: List[RouteState] = []
            for route in result["routes"]:
                stops = route.get("stops", [])
                customers_in_route = [
                    stop
                    for stop in stops
                    if stop.get("customer_id") not in (0, None)
                ]
                if not customers_in_route:
                    continue
                vehicle = optimizer.vehicle_by_type[route["vehicle_type"]]
                new_routes.append(
                    RouteState(
                        vehicle,
                        [
                            optimizer.customer_by_id[
                                int(customer["customer_id"])
                            ]
                            for customer in customers_in_route
                        ],
                        start_minute=int(stops[0].get("arrival_time", 480)),
                    )
                )
            old_cost = optimizer.route_cost(
                route_a
            ) + optimizer.route_cost(route_b)
            new_cost = sum(
                optimizer.route_cost(route) for route in new_routes
            )
            if new_cost < old_cost - 1e-9:
                while len(new_routes) < 2:
                    new_routes.append(
                        RouteState(route_a.vehicle, [], route_a.start_minute)
                    )
                routes[a_index] = new_routes[0]
                routes[b_index] = new_routes[1]
                accepted += 1
                print(
                    f"pair {a_index}-{b_index}: {old_cost:.2f} -> "
                    f"{new_cost:.2f}"
                )

    optimizer.optimize_start_times(routes)
    candidate = _build_solution(routes, CONFIG, depot, base, 0.0)
    after = calculate_green_cost(candidate, CONFIG, params)["total_cost"]
    print(
        f"pairs accepted: {accepted}, actual -> {after:.2f}, "
        f"distance {candidate['total_distance']:.1f}km, "
        f"late {candidate['total_late_minutes']}"
    )


if __name__ == "__main__":
    main()
