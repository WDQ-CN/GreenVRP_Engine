"""CP-SAT route-pair re-optimization for the final solution.

Each pair of routes is re-solved as a two-vehicle VRPTW (capacity, hard time
windows, 18:00 return) with static daytime travel times.  The original pair is
used as a hint; the model minimizes distance, then the candidate is filtered by
the exact five-factor ALNS cost.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from config.constants import WORK_DAY_END_MIN, WORK_DAY_START_MIN
from utils.geo import haversine_distance

from .alns import RouteState, _ALNSOptimizer

TIME_SCALE = 10
DIST_SCALE = 1000


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
        (customer["lat"], customer["lon"]) for customer in customers
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

    def customer_node(k: int, i: int) -> int:
        return k * (n + 2) + 2 + i

    arc_vars: Dict[Tuple[int, int, int], Any] = {}
    loops: Dict[Tuple[int, int], Any] = {}
    for k in range(2):
        start = k * (n + 2)
        end = start + 1
        empty = model.NewBoolVar(f"empty_{k}")
        arc_vars[(k, start, end)] = empty
        for i in range(n):
            node_i = customer_node(k, i)
            arc_vars[(k, start, node_i)] = model.NewBoolVar(f"s_{k}_{i}")
            arc_vars[(k, node_i, end)] = model.NewBoolVar(f"e_{k}_{i}")
            loop = model.NewBoolVar(f"l_{k}_{i}")
            loops[(k, i)] = loop
            for j in range(n):
                if i != j:
                    arc_vars[(k, node_i, customer_node(k, j))] = (
                        model.NewBoolVar(f"a_{k}_{i}_{j}")
                    )

    for k in range(2):
        start = k * (n + 2)
        end = start + 1
        vehicle_arcs = [(start, end, arc_vars[(k, start, end)])]
        for i in range(n):
            node_i = customer_node(k, i)
            vehicle_arcs.append((start, node_i, arc_vars[(k, start, node_i)]))
            vehicle_arcs.append((node_i, end, arc_vars[(k, node_i, end)]))
            vehicle_arcs.append((node_i, node_i, loops[(k, i)]))
            for j in range(n):
                if i != j:
                    vehicle_arcs.append(
                        (
                            node_i,
                            customer_node(k, j),
                            arc_vars[(k, node_i, customer_node(k, j))],
                        )
                    )
        close_arc = model.NewBoolVar(f"close_{k}")
        model.Add(close_arc == 1)
        vehicle_arcs.append((end, start, close_arc))
        model.AddCircuit(vehicle_arcs)

    assigned: Dict[Tuple[int, int], Any] = {}
    for i in range(n):
        y0 = model.NewBoolVar(f"y0_{i}")
        y1 = model.NewBoolVar(f"y1_{i}")
        model.Add(y0 + y1 == 1)
        model.Add(loops[(0, i)] == 1 - y0)
        model.Add(loops[(1, i)] == 1 - y1)
        assigned[(0, i)] = y0
        assigned[(1, i)] = y1

    for k in range(2):
        start = k * (n + 2)
        end = start + 1
        for i in range(n):
            y = assigned[(k, i)]
            model.AddImplication(arc_vars[(k, start, customer_node(k, i))], y)
            model.AddImplication(arc_vars[(k, customer_node(k, i), end)], y)
            for j in range(n):
                if i != j:
                    model.AddImplication(
                        arc_vars[
                            (k, customer_node(k, i), customer_node(k, j))
                        ],
                        y,
                    )

    for k in range(2):
        model.Add(
            sum(
                int(round(float(customer["demand"]))) * assigned[(k, i)]
                for i, customer in enumerate(customers)
            )
            <= int(round(vehicles[k].capacity))
        )

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
        t[(k, end)] = model.NewIntVar(
            0, WORK_DAY_END_MIN * TIME_SCALE, f"t_end_{k}"
        )
        for i in range(n):
            t[(k, customer_node(k, i))] = model.NewIntVar(
                0,
                WORK_DAY_END_MIN * TIME_SCALE,
                f"t_{k}_{i}",
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
                from_node = start if i == 0 else customer_node(k, i - 1)
                to_node = end if j == 0 else customer_node(k, j - 1)
                key = (k, from_node, to_node)
                if key not in arc_vars:
                    continue
                arc = arc_vars[key]
                service_i = (
                    0.0
                    if i == 0
                    else float(customers[i - 1].get("service_time", 0) or 0)
                )
                travel = (
                    distances[i][j]
                    / max(vehicle.speed_kmh, 0.1)
                    * 60.0
                    * TIME_SCALE
                )
                model.Add(
                    t[(k, to_node)]
                    >= t[(k, from_node)]
                    + int(round(service_i * TIME_SCALE))
                    + int(round(travel))
                    - big_m * (1 - arc)
                )

    distance_terms = []
    for k in range(2):
        for i in range(n + 1):
            for j in range(n + 1):
                if i == j:
                    continue
                from_node = k * (n + 2) if i == 0 else customer_node(k, i - 1)
                to_node = k * (n + 2) + 1 if j == 0 else customer_node(k, j - 1)
                key = (k, from_node, to_node)
                if key not in arc_vars:
                    continue
                distance_terms.append(
                    int(round(distances[i][j] * DIST_SCALE)) * arc_vars[key]
                )
    model.Minimize(sum(distance_terms))

    sequence_by_vehicle = [
        [int(customer["customer_id"]) for customer in route_a.customers],
        [int(customer["customer_id"]) for customer in route_b.customers],
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
            int(
                round(
                    float(
                        route_a.start_minute if k == 0 else route_b.start_minute
                    )
                )
            )
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
                to_node = end if i == 0 else customer_node(k, i - 1)
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
        result_routes.append(
            RouteState(
                vehicles[k],
                order,
                start_minute=solver.Value(t[(k, start)]) // TIME_SCALE,
            )
        )
    return result_routes or None


def improve_pairs_with_cpsat(
    optimizer: _ALNSOptimizer,
    routes: List[RouteState],
    depot: Dict[str, Any],
    time_limit_per_pair: float = 8.0,
) -> int:
    moves = 0
    for a_index in range(len(routes)):
        if not routes[a_index].customers:
            continue
        for b_index in range(a_index + 1, len(routes)):
            if not routes[b_index].customers:
                continue
            new_routes = _solve_pair(
                depot,
                routes[a_index],
                routes[b_index],
                time_limit_per_pair,
            )
            if not new_routes:
                continue
            optimizer.optimize_start_times(new_routes)
            old_cost = optimizer.route_cost(
                routes[a_index]
            ) + optimizer.route_cost(routes[b_index])
            new_cost = sum(optimizer.route_cost(route) for route in new_routes)
            if new_cost >= old_cost - 1e-9:
                continue
            while len(new_routes) < 2:
                new_routes.append(
                    RouteState(routes[a_index].vehicle, [], WORK_DAY_START_MIN)
                )
            routes[a_index] = new_routes[0]
            routes[b_index] = new_routes[1]
            moves += 1
    if moves:
        optimizer.optimize_start_times(routes)
    return moves
