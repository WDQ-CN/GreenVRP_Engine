"""Experiment: exact CP-SAT re-optimization for each route pair.

The final schedules operate in the daytime speed band, so this model uses
static daytime travel times, hard time windows, capacity and the 18:00 return
limit.  It minimizes distance; the resulting pair is then filtered with the
exact five-factor ALNS cost.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ortools.sat.python import cp_model

from config.constants import DEFAULT_PARAMS, WORK_DAY_END_MIN, WORK_DAY_START_MIN
from core.cost import calculate_green_cost
from optimization.alns import (
    RouteState,
    _ALNSOptimizer,
    _build_solution,
    _build_vehicle_pool,
    _extract_initial,
)
from utils.geo import haversine_distance

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
TIME_SCALE = 10
DIST_SCALE = 1000


def _load(name: str) -> Dict[str, Any]:
    with (ARTIFACTS / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _solve_pair(
    depot: Dict[str, Any],
    route_a: RouteState,
    route_b: RouteState,
    time_limit: float,
) -> Optional[List[RouteState]]:
    customers = list(route_a.customers) + list(route_b.customers)
    if len(customers) < 2:
        return None
    vehicles = [route_a.vehicle, route_b.vehicle]
    n = len(customers)
    locations = [(depot["lat"], depot["lon"])] + [
        (c["lat"], c["lon"]) for c in customers
    ]
    distances = [
        [
            haversine_distance(
                locations[i][0], locations[i][1],
                locations[j][0], locations[j][1],
            )
            for j in range(n + 1)
        ]
        for i in range(n + 1)
    ]

    model = cp_model.CpModel()
    # Nodes: start/end for each vehicle, then per-vehicle customer copies.
    def customer_node(k: int, i: int) -> int:
        return k * (n + 2) + 2 + i

    arcs: List[Tuple[int, int, Any]] = []
    arc_vars: Dict[Tuple[int, int, int], Any] = {}
    loops: Dict[Tuple[int, int], Any] = {}

    for k in range(2):
        start = k * (n + 2)
        end = start + 1
        # empty route
        empty = model.NewBoolVar(f"empty_{k}")
        arcs.append((start, end, empty))
        arc_vars[(k, start, end)] = empty
        for i in range(n):
            node_i = customer_node(k, i)
            s_arc = model.NewBoolVar(f"s_{k}_{i}")
            e_arc = model.NewBoolVar(f"e_{k}_{i}")
            loop = model.NewBoolVar(f"l_{k}_{i}")
            arcs.append((start, node_i, s_arc))
            arcs.append((node_i, end, e_arc))
            arcs.append((node_i, node_i, loop))
            arc_vars[(k, start, node_i)] = s_arc
            arc_vars[(k, node_i, end)] = e_arc
            loops[(k, i)] = loop
            for j in range(n):
                if i == j:
                    continue
                node_j = customer_node(k, j)
                arc = model.NewBoolVar(f"a_{k}_{i}_{j}")
                arcs.append((node_i, node_j, arc))
                arc_vars[(k, node_i, node_j)] = arc

    for k in range(2):
        start = k * (n + 2)
        end = start + 1
        # Build the circuit only with this vehicle's start/end and its own
        # customer copies; shared customer nodes are not allowed by AddCircuit.
        vehicle_arcs = [(start, end, arc_vars[(k, start, end)])]
        for i in range(n):
            vehicle_arcs.append(
                (start, customer_node(k, i), arc_vars[(k, start, customer_node(k, i))])
            )
            vehicle_arcs.append(
                (customer_node(k, i), end, arc_vars[(k, customer_node(k, i), end)])
            )
            vehicle_arcs.append(
                (customer_node(k, i), customer_node(k, i), loops[(k, i)])
            )
            for j in range(n):
                if i != j:
                    vehicle_arcs.append(
                        (
                            customer_node(k, i),
                            customer_node(k, j),
                            arc_vars[(k, customer_node(k, i), customer_node(k, j))],
                        )
                    )
        # AddCircuit must cover every node; each vehicle has an isolated node
        # block, so no cross-vehicle self-loops are required.
        close_arc = model.NewBoolVar(f"close_{k}")
        model.Add(close_arc == 1)
        vehicle_arcs.append((end, start, close_arc))
        model.AddCircuit(vehicle_arcs)

    assigned = {}
    for i in range(n):
        y0 = model.NewBoolVar(f"y0_{i}")
        y1 = model.NewBoolVar(f"y1_{i}")
        model.Add(y0 + y1 == 1)
        model.Add(loops[(0, i)] == 1 - y0)
        model.Add(loops[(1, i)] == 1 - y1)
        assigned[(0, i)] = y0
        assigned[(1, i)] = y1

    # Link real arcs to assignment.
    for k in range(2):
        end = k * (n + 2) + 1
        for i in range(n):
            y = assigned[(k, i)]
            model.AddImplication(
                arc_vars[(k, k * (n + 2), customer_node(k, i))], y
            )
            model.AddImplication(arc_vars[(k, customer_node(k, i), end)], y)
            for j in range(n):
                if i != j:
                    model.AddImplication(
                        arc_vars[(k, customer_node(k, i), customer_node(k, j))], y
                    )

    # Capacity.
    for k in range(2):
        model.Add(
            sum(
                int(round(float(c["demand"]))) * assigned[(k, i)]
                for i, c in enumerate(customers)
            )
            <= int(round(vehicles[k].capacity))
        )

    # Time variables.
    big_m = 20000
    t: Dict[Tuple[int, int], Any] = {}
    for k in range(2):
        start = k * (n + 2)
        end = start + 1
        t[(k, start)] = model.NewIntVar(
            WORK_DAY_START_MIN * TIME_SCALE,
            WORK_DAY_END_MIN * TIME_SCALE,
            f"t_start_{k}",
        )
        t[(k, end)] = model.NewIntVar(0, WORK_DAY_END_MIN * TIME_SCALE, f"t_end_{k}")
        for i in range(n):
            node = customer_node(k, i)
            t[(k, node)] = model.NewIntVar(
                0, WORK_DAY_END_MIN * TIME_SCALE, f"t_{k}_{i}"
            )

    for i, customer in enumerate(customers):
        earliest = int(round(float(customer.get("tw_earliest", 480)))) * TIME_SCALE
        latest = int(round(float(customer.get("tw_latest", 1080)))) * TIME_SCALE
        for k in range(2):
            node = customer_node(k, i)
            y = assigned[(k, i)]
            model.Add(t[(k, node)] >= earliest).OnlyEnforceIf(y)
            model.Add(t[(k, node)] <= latest).OnlyEnforceIf(y)
            model.Add(t[(k, node)] <= latest + big_m * (1 - y))
            model.Add(t[(k, node)] == 0).OnlyEnforceIf(y.Not())

    for k in range(2):
        start = k * (n + 2)
        end = start + 1
        vehicle = vehicles[k]
        for i in range(n + 1):
            for j in range(n + 1):
                if i == j:
                    continue
                if i == 0:
                    from_node = start
                else:
                    from_node = customer_node(k, i - 1)
                if j == 0:
                    to_node = end
                else:
                    to_node = customer_node(k, j - 1)
                key = (k, from_node, to_node)
                if key not in arc_vars:
                    continue
                arc = arc_vars[key]
                service_i = 0 if i == 0 else float(customers[i - 1].get("service_time", 0) or 0)
                travel = (
                    distances[i][j] / max(vehicle.speed_kmh, 0.1) * 60.0 * TIME_SCALE
                )
                travel_int = int(round(travel))
                service_int = int(round(service_i * TIME_SCALE))
                model.Add(
                    t[(k, to_node)]
                    >= t[(k, from_node)] + service_int + travel_int
                    - big_m * (1 - arc)
                )

    # Objective: total distance.
    distance_terms = []
    for k in range(2):
        for i in range(n + 1):
            for j in range(n + 1):
                if i == j:
                    continue
                if i == 0:
                    from_node = k * (n + 2)
                else:
                    from_node = customer_node(k, i - 1)
                if j == 0:
                    to_node = k * (n + 2) + 1
                else:
                    to_node = customer_node(k, j - 1)
                key = (k, from_node, to_node)
                if key not in arc_vars:
                    continue
                arc = arc_vars[key]
                distance_terms.append(
                    int(round(distances[i][j] * DIST_SCALE)) * arc
                )
    model.Minimize(sum(distance_terms))

    try:
        model.Validate()
    except Exception as exc:
        print(f"invalid model: {exc}")
        return None

    import os

    hint_mode = True
    if hint_mode:
        sequence_by_vehicle = [
            [int(c["customer_id"]) for c in route_a.customers],
            [int(c["customer_id"]) for c in route_b.customers],
        ]
        id_to_index = {
            int(customer["customer_id"]): i
            for i, customer in enumerate(customers)
        }
        arc_hints: Dict[Tuple[int, int, int], int] = {
            key: 0 for key in arc_vars
        }
        for k in range(2):
            sequence = sequence_by_vehicle[k]
            assigned_ids = set(sequence)
            start = k * (n + 2)
            end = start + 1
            arc_hints[(k, start, end)] = 0
            if sequence:
                first = customer_node(k, id_to_index[sequence[0]])
                last = customer_node(k, id_to_index[sequence[-1]])
                arc_hints[(k, start, first)] = 1
                arc_hints[(k, last, end)] = 1
                for left, right in zip(sequence, sequence[1:]):
                    arc_hints[
                        (
                            k,
                            customer_node(k, id_to_index[left]),
                            customer_node(k, id_to_index[right]),
                        )
                    ] = 1
            for i, customer in enumerate(customers):
                is_assigned = int(customer["customer_id"]) in assigned_ids
                model.AddHint(assigned[(k, i)], 1 if is_assigned else 0)
                model.AddHint(loops[(k, i)], 0 if is_assigned else 1)
                model.AddHint(
                    t[(k, customer_node(k, i))],
                    (
                        int(round(float(customer.get("arrival_time", 480))))
                        * TIME_SCALE
                        if is_assigned
                        else 0
                    ),
                )
            model.AddHint(
                t[(k, start)],
                int(round(float(route_a.start_minute if k == 0 else route_b.start_minute)))
                * TIME_SCALE,
            )
            model.AddHint(t[(k, end)], WORK_DAY_END_MIN * TIME_SCALE)
        for (k, i, j), variable in arc_vars.items():
            model.AddHint(variable, arc_hints.get((k, i, j), 0))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(1.0, time_limit)
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if hint_mode:
            print(f"hint infeasible: {solver.StatusName(status)}")
        return None

    result_routes: List[RouteState] = []
    for k in range(2):
        start = k * (n + 2)
        end = start + 1
        if solver.Value(arc_vars[(k, start, end)]):
            continue
        order = []
        current = start
        guard = 0
        while current != end and guard <= n + 2:
            guard += 1
            next_node = None
            for i in range(n + 1):
                if i == 0:
                    to_node = end
                else:
                    to_node = customer_node(k, i - 1)
                key = (k, current, to_node)
                if key in arc_vars and solver.Value(arc_vars[key]):
                    next_node = to_node
                    if i > 0:
                        order.append(customers[i - 1])
                    break
            if next_node is None:
                return None
            current = next_node
        if not order:
            continue
        start_minute = solver.Value(t[(k, start)]) // TIME_SCALE
        result_routes.append(
            RouteState(
                vehicles[k],
                order,
                start_minute=start_minute,
            )
        )
    return result_routes or None


def main() -> None:
    solution_name = sys.argv[1] if len(sys.argv) > 1 else "full_t30_probe_final.json"
    time_limit = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
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
    attempts = 0
    for a_index in range(len(routes)):
        if not routes[a_index].customers:
            continue
        for b_index in range(a_index + 1, len(routes)):
            if not routes[b_index].customers:
                continue
            attempts += 1
            started = time.perf_counter()
            new_routes = _solve_pair(
                depot, routes[a_index], routes[b_index], time_limit
            )
            elapsed = time.perf_counter() - started
            if not new_routes:
                print(f"pair {a_index}-{b_index}: no CP-SAT solution ({elapsed:.1f}s)")
                continue
            optimizer.optimize_start_times(new_routes)
            old_cost = optimizer.route_cost(
                routes[a_index]
            ) + optimizer.route_cost(routes[b_index])
            new_cost = sum(
                optimizer.route_cost(route) for route in new_routes
            )
            print(
                f"pair {a_index}-{b_index}: {old_cost:.2f} -> "
                f"{new_cost:.2f} ({elapsed:.1f}s)"
            )
            if new_cost < old_cost - 1e-9:
                while len(new_routes) < 2:
                    new_routes.append(
                        RouteState(routes[a_index].vehicle, [], 480)
                    )
                routes[a_index] = new_routes[0]
                routes[b_index] = new_routes[1]
                accepted += 1

    optimizer.optimize_start_times(routes)
    candidate = _build_solution(routes, CONFIG, depot, base, 0.0)
    after = calculate_green_cost(candidate, CONFIG, params)["total_cost"]
    print(
        f"attempts {attempts}, accepted {accepted}, "
        f"actual -> {after:.2f}, distance {candidate['total_distance']:.1f}km, "
        f"late {candidate['total_late_minutes']}"
    )


if __name__ == "__main__":
    main()
