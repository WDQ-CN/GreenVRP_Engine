"""Route-pool recombination for the ALNS post-optimizer.

The ALNS run records high-quality routes from successive best solutions.  The
pool is recombined with a CP-SAT set-partitioning model: every customer must be
covered exactly once, and each vehicle type is limited by the fleet size.  This
lets the search mix routes from different local optima without re-inserting
customers one by one.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import List, Optional, Tuple

from ortools.sat.python import cp_model

from .alns import RouteState, _ALNSOptimizer


def recombine_route_pool(
    optimizer: _ALNSOptimizer,
    time_limit: float = 5.0,
    max_routes: int = 800,
    random_seed: Optional[int] = None,
) -> Optional[Tuple[List[RouteState], float]]:
    """Solve the route-pool set-partitioning model.

    Returns (selected_routes, internal_cost) or None when the pool cannot be
    recombined into a complete solution.
    """
    pool = optimizer.route_pool
    if len(pool) < 2 or time_limit <= 0:
        return None

    customer_ids = set(optimizer.customer_by_id.keys())
    entries = []
    for (vehicle_type, _sorted_ids), (ids, metrics, _start) in pool.items():
        if math.isfinite(metrics.cost):
            entries.append((vehicle_type, ids, metrics.cost))
    if not entries:
        return None

    entries.sort(key=lambda item: item[2])
    if len(entries) > max_routes:
        entries = entries[:max_routes]

    covered = set()
    for _vehicle_type, ids, _cost in entries:
        covered.update(ids)
    if covered != customer_ids:
        return None

    model = cp_model.CpModel()
    variables = []
    coverage = {customer_id: [] for customer_id in customer_ids}
    by_type = {}
    scaled_costs = []

    for index, (vehicle_type, ids, cost) in enumerate(entries):
        variable = model.NewBoolVar(f"route_{index}")
        variables.append(variable)
        scaled_costs.append(max(0, int(round(cost * 100))))
        for customer_id in ids:
            coverage[customer_id].append(variable)
        by_type.setdefault(vehicle_type, []).append(variable)

    for customer_id, customer_variables in coverage.items():
        model.Add(sum(customer_variables) == 1)
    for vehicle_type, type_variables in by_type.items():
        model.Add(
            sum(type_variables)
            <= optimizer.fleet_counts.get(vehicle_type, 0)
        )
    model.Minimize(
        sum(cost * variable for cost, variable in zip(scaled_costs, variables))
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(0.1, time_limit)
    solver.parameters.num_search_workers = 8
    if random_seed is not None:
        solver.parameters.random_seed = int(random_seed)
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    selected: List[RouteState] = []
    total_cost = 0.0
    next_vehicle_id = 0
    for index, variable in enumerate(variables):
        if solver.Value(variable):
            vehicle_type, ids, cost = entries[index]
            vehicle = replace(
                optimizer.vehicle_by_type[vehicle_type],
                vehicle_id=next_vehicle_id,
            )
            next_vehicle_id += 1
            selected.append(
                RouteState(
                    vehicle=vehicle,
                    customers=[
                        optimizer.customer_by_id[customer_id]
                        for customer_id in ids
                    ],
                )
            )
            total_cost += cost

    if not selected:
        return None
    return selected, total_cost
