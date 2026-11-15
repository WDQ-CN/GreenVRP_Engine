"""Experiment: recombine routes from several saved solutions with CP-SAT."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.constants import DEFAULT_PARAMS
from core.cost import calculate_green_cost
from optimization.alns import (
    RouteState,
    _ALNSOptimizer,
    _build_solution,
    _build_vehicle_pool,
    _extract_initial,
)
from optimization.recombine import recombine_route_pool

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


def _add_solution(
    optimizer: _ALNSOptimizer, solution: Dict[str, Any], label: str
) -> None:
    for route in solution.get("routes", []):
        vehicle_type = route.get("vehicle_type")
        vehicle = optimizer.vehicle_by_type.get(vehicle_type)
        if vehicle is None:
            continue
        customers = [
            stop
            for stop in route.get("stops", [])
            if stop.get("customer_id") not in (0, None)
        ]
        if customers:
            start_minute = int(
                (route.get("stops") or [{}])[0].get("arrival_time", 480)
            )
            optimizer._record_pool(
                [RouteState(vehicle, customers, start_minute=start_minute)]
            )
    print(f"pool after {label}: {len(optimizer.route_pool)} routes")


def main() -> None:
    base = _load("six_gls_recombine_sol.json")
    pool = _build_vehicle_pool(CONFIG)
    routes, available, depot = _extract_initial(base, pool)
    assert routes is not None and depot is not None
    params = {**DEFAULT_PARAMS, "late_penalty_per_min": 10.0}
    optimizer = _ALNSOptimizer(routes, available, depot, CONFIG, params, seed=0)

    solutions = [
        ("stage1_gls", "stage1_n100_seed42_t30_six_gls.json"),
        ("stage1_tabu", "stage1_n100_seed42_t30_six_tabu.json"),
        ("stage1_sa", "stage1_n100_seed42_t30_six_sa.json"),
        ("stage1_pci", "stage1_n100_seed42_t30_six_pci.json"),
        ("alns_gls", "six_gls_recombine_sol.json"),
        ("alns_tabu", "six_tabu_sol.json"),
        ("alns_sa", "six_sa_sol.json"),
        ("alns_pci", "six_pci_sol.json"),
        ("alns_seed47", "six_gls_seed47_sol.json"),
        ("alns_seed48", "six_gls_seed48_sol.json"),
        ("alns_seed49", "six_gls_seed49_sol.json"),
        ("alns_seed50", "six_gls_seed50_sol.json"),
        ("alns_seed56", "six_gls_seed56_sol.json"),
    ]
    best_input_cost = float("inf")
    for label, filename in solutions:
        solution = _load(filename)
        cost = calculate_green_cost(solution, CONFIG, params)["total_cost"]
        print(f"{label}: cost {cost:.2f}")
        best_input_cost = min(best_input_cost, cost)
        _add_solution(optimizer, solution, label)

    selected, internal_cost = recombine_route_pool(optimizer, time_limit=30.0) or (
        None,
        None,
    )
    print(f"input best: {best_input_cost:.2f}")
    print(f"pool: {len(optimizer.route_pool)} routes")
    if selected is None:
        print("recombination infeasible")
        return
    optimizer.optimize_start_times(selected)
    selected = [
        optimizer._polish_route(route, max_passes=4) for route in selected
    ]
    optimizer.optimize_start_times(selected)
    internal_cost = sum(optimizer.route_cost(route) for route in selected)
    print(f"recombined internal cost: {internal_cost:.2f}")
    candidate = _build_solution(selected, CONFIG, depot, base, 0.0)
    cost = calculate_green_cost(candidate, CONFIG, params)
    print(
        f"recombined actual: {cost['total_cost']:.2f} | "
        f"carbon {cost['carbon_emission_kg']:.2f}kg | "
        f"late {candidate.get('total_late_minutes')} | "
        f"vehicles {sum(candidate.get('vehicles_used', {}).values())} | "
        f"distance {cost['total_distance_km']:.1f}km"
    )


if __name__ == "__main__":
    main()
