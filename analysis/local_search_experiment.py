"""Experiment: deterministic 2-opt* inter-route polish on a saved solution."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.constants import DEFAULT_PARAMS
from core.cost import calculate_green_cost
from optimization.alns import (
    INF,
    RouteState,
    _ALNSOptimizer,
    _build_solution,
    _build_vehicle_pool,
    _extract_initial,
)

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


def _two_opt_star(
    optimizer: _ALNSOptimizer,
    routes: List[RouteState],
    deadline: float,
) -> int:
    moves = 0
    while time.perf_counter() < deadline:
        improved = False
        for a_index in range(len(routes)):
            if time.perf_counter() >= deadline:
                break
            route_a = routes[a_index]
            ids_a = [int(c["customer_id"]) for c in route_a.customers]
            demand_a = [optimizer.info_by_id[cid][1] for cid in ids_a]
            prefix_a = [0.0]
            for value in demand_a:
                prefix_a.append(prefix_a[-1] + value)
            total_a = prefix_a[-1]
            cap_a = route_a.vehicle.capacity

            for b_index in range(a_index + 1, len(routes)):
                if time.perf_counter() >= deadline:
                    break
                route_b = routes[b_index]
                ids_b = [int(c["customer_id"]) for c in route_b.customers]
                demand_b = [optimizer.info_by_id[cid][1] for cid in ids_b]
                prefix_b = [0.0]
                for value in demand_b:
                    prefix_b.append(prefix_b[-1] + value)
                total_b = prefix_b[-1]
                cap_b = route_b.vehicle.capacity
                old_cost = optimizer.route_cost(route_a) + optimizer.route_cost(route_b)

                best: Tuple[float, int, int, List[int], List[int]] | None = None
                for i in range(len(ids_a) + 1):
                    for j in range(len(ids_b) + 1):
                        if i == 0 and j == 0:
                            continue
                        if i == len(ids_a) and j == len(ids_b):
                            continue
                        new_ids_a = ids_a[:i] + ids_b[j:]
                        new_ids_b = ids_b[:j] + ids_a[i:]
                        if not new_ids_a or not new_ids_b:
                            continue
                        load_a = prefix_a[i] + (total_b - prefix_b[j])
                        load_b = prefix_b[j] + (total_a - prefix_a[i])
                        if load_a > cap_a + 1e-9 or load_b > cap_b + 1e-9:
                            continue
                        cost_a = optimizer._evaluate(
                            route_a.vehicle.vehicle_type,
                            tuple(new_ids_a),
                            route_a.start_minute,
                        ).cost
                        if cost_a >= INF:
                            continue
                        cost_b = optimizer._evaluate(
                            route_b.vehicle.vehicle_type,
                            tuple(new_ids_b),
                            route_b.start_minute,
                        ).cost
                        total = cost_a + cost_b
                        if total < old_cost - 1e-9 and (
                            best is None or total < best[0]
                        ):
                            best = (total, i, j, new_ids_a, new_ids_b)

                if best is not None:
                    _, i, j, new_ids_a, new_ids_b = best
                    routes[a_index] = RouteState(
                        route_a.vehicle,
                        [optimizer.customer_by_id[cid] for cid in new_ids_a],
                        start_minute=route_a.start_minute,
                    )
                    routes[b_index] = RouteState(
                        route_b.vehicle,
                        [optimizer.customer_by_id[cid] for cid in new_ids_b],
                        start_minute=route_b.start_minute,
                    )
                    optimizer.optimize_start_times(
                        [routes[a_index], routes[b_index]]
                    )
                    moves += 1
                    improved = True
                    break
            if improved:
                break
        if not improved:
            break
    return moves


def main() -> None:
    solution_name = (
        sys.argv[1] if len(sys.argv) > 1 else "six_gls_seed91_sol.json"
    )
    base = _load(solution_name)
    params = {**DEFAULT_PARAMS, "late_penalty_per_min": 10.0}
    pool = _build_vehicle_pool(CONFIG)
    routes, available, depot = _extract_initial(base, pool)
    assert routes is not None and available is not None and depot is not None
    optimizer = _ALNSOptimizer(routes, available, depot, CONFIG, params, 0)

    optimizer.optimize_start_times(optimizer.routes)
    before_internal = sum(
        optimizer.route_cost(route) for route in optimizer.routes
    )
    before_actual = calculate_green_cost(base, CONFIG, params)["total_cost"]
    print(
        f"{solution_name}: internal {before_internal:.2f}, "
        f"actual {before_actual:.2f}, routes {len(optimizer.routes)}"
    )

    started = time.perf_counter()
    moves = _two_opt_star(
        optimizer, optimizer.routes, started + 15.0
    )
    vnd_moves = optimizer.inter_route_vnd(optimizer.routes, 15.0)
    seg_moves = optimizer.inter_route_segment_vnd(optimizer.routes, 15.0)
    pair_moves = optimizer.pairwise_alns(optimizer.routes, 1500)
    optimizer.optimize_start_times(optimizer.routes)
    after_internal = sum(
        optimizer.route_cost(route) for route in optimizer.routes
    )
    candidate = _build_solution(
        optimizer.routes, CONFIG, depot, base, time.perf_counter() - started
    )
    after_actual = calculate_green_cost(candidate, CONFIG, params)["total_cost"]
    print(
        f"2-opt* moves: {moves}, VND moves: {vnd_moves}, "
        f"segment moves: {seg_moves}, pair moves: {pair_moves}, "
        f"internal -> {after_internal:.2f}, "
        f"actual -> {after_actual:.2f}, "
        f"distance {candidate['total_distance']:.1f}km, "
        f"late {candidate['total_late_minutes']}"
    )


if __name__ == "__main__":
    main()
