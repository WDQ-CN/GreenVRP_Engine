"""ALNS post-optimizer for the heterogeneous-fleet green VRPTW.

The destroy/repair design follows the IALNS/ALNS literature used in this
project, in particular Nan et al. (2021), Ropke & Pisinger (2006),
Demir et al. (2012), and Liu et al. (2023).  It starts from the OR-Tools
solution and improves it with adaptive ruin-and-recreate operators.
"""

from __future__ import annotations

import copy
import math
import random
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple

from config.constants import (
    DEFAULT_PARAMS,
    DIESEL_CO2_FACTOR,
    FUEL_EMPTY_LOAD_RATIO,
    FUEL_FULL_LOAD_RATIO,
    WORK_DAY_END_MIN,
    WORK_DAY_START_MIN,
)
from utils.geo import haversine_distance
from utils.time_profile import (
    fuel_speed_factor,
    speed_multiplier,
    travel_time_minutes,
)

INF = float("inf")


@dataclass(frozen=True)
class Vehicle:
    vehicle_id: int
    vehicle_type: str
    capacity: float
    fixed_cost: float
    speed_kmh: float
    fuel_per_100km: float
    fuel_empty_per_100km: float
    fuel_full_per_100km: float
    color: str


@dataclass
class RouteState:
    vehicle: Vehicle
    customers: List[Dict[str, Any]]
    start_minute: int = WORK_DAY_START_MIN


@dataclass(frozen=True)
class RouteMetrics:
    cost: float
    distance_km: float
    fuel_liters: float
    late_minutes: int
    driving_min: float
    waiting_min: float
    service_min: float


def _build_vehicle_pool(
    vehicle_config: Dict[str, Dict[str, Any]],
) -> List[Vehicle]:
    pool: List[Vehicle] = []
    vehicle_id = 0
    for vehicle_type, config in vehicle_config.items():
        fuel = float(config.get("fuel_per_100km", 12.0))
        fuel_empty_value = config.get("fuel_empty_per_100km")
        fuel_full_value = config.get("fuel_full_per_100km")
        fuel_empty = (
            float(fuel_empty_value)
            if fuel_empty_value is not None
            else fuel * FUEL_EMPTY_LOAD_RATIO
        )
        fuel_full = (
            float(fuel_full_value)
            if fuel_full_value is not None
            else fuel * FUEL_FULL_LOAD_RATIO
        )
        for _ in range(int(config.get("count", 0))):
            pool.append(
                Vehicle(
                    vehicle_id=vehicle_id,
                    vehicle_type=vehicle_type,
                    capacity=max(float(config.get("capacity", 0.0)), 1.0),
                    fixed_cost=float(config.get("fixed_cost", 0.0)),
                    speed_kmh=max(float(config.get("speed_kmh", 40.0)), 1.0),
                    fuel_per_100km=max(fuel, 0.0),
                    fuel_empty_per_100km=max(fuel_empty, 0.0),
                    fuel_full_per_100km=max(fuel_full, 0.0),
                    color=str(config.get("color", "#1f77b4")),
                )
            )
            vehicle_id += 1
    return pool


def _extract_initial(
    solution: Dict[str, Any],
    pool: List[Vehicle],
) -> Tuple[Optional[List[RouteState]], Optional[List[Vehicle]], Optional[Dict[str, Any]]]:
    by_id = {vehicle.vehicle_id: vehicle for vehicle in pool}

    depot: Optional[Dict[str, Any]] = None
    routes: List[RouteState] = []
    used_ids = set()

    for route in solution.get("routes", []):
        stops = route.get("stops", [])
        if not isinstance(stops, (list, tuple)) or not stops:
            continue

        for stop in stops:
            if stop.get("customer_id") == 0 or stop.get("node") == 0:
                depot = stop
                break

        customers = [
            copy.deepcopy(stop)
            for stop in stops
            if stop.get("customer_id") not in (0, None)
            and (stop.get("node") or 0) != 0
        ]
        if not customers:
            continue

        vehicle_type = route.get("vehicle_type")
        vehicle = by_id.get(route.get("vehicle_id"))
        if vehicle is not None and (
            vehicle.vehicle_type != vehicle_type
            or vehicle.vehicle_id in used_ids
        ):
            vehicle = None
        if vehicle is None:
            vehicle = next(
                (
                    candidate
                    for candidate in pool
                    if candidate.vehicle_type == vehicle_type
                    and candidate.vehicle_id not in used_ids
                ),
                None,
            )
        if vehicle is None:
            # 无法在不超出车队数量的前提下分配车辆
            return None, None, None

        used_ids.add(vehicle.vehicle_id)
        routes.append(RouteState(vehicle=vehicle, customers=customers))

    if not routes or depot is None:
        return None, None, None

    available = [vehicle for vehicle in pool if vehicle.vehicle_id not in used_ids]
    return routes, available, depot


class _ALNSOptimizer:
    def __init__(
        self,
        routes: List[RouteState],
        available: List[Vehicle],
        depot: Dict[str, Any],
        vehicle_config: Dict[str, Dict[str, Any]],
        params: Dict[str, Any],
        seed: int,
    ) -> None:
        self.routes = routes
        self.available = available
        self.depot = depot
        self.params = params
        self.rng = random.Random(seed)
        self.fleet_counts = {
            vehicle_type: int(config.get("count", 0))
            for vehicle_type, config in vehicle_config.items()
        }
        self.route_pool: Dict[
            Tuple[str, Tuple[int, ...]],
            Tuple[Tuple[int, ...], RouteMetrics, int],
        ] = {}

        self.fuel_price = float(params.get("fuel_price", 7.5))
        self.carbon_price = float(params.get("carbon_price", 0.08))
        self.late_penalty = float(params.get("late_penalty_per_min", 10.0))
        self.hourly_wage = float(params.get("hourly_wage", 50.0))
        self.temperature_ratio = float(
            params.get("alns_temperature_ratio", 0.02)
        )
        self.cooling_factor = float(
            params.get("alns_cooling_factor", 0.9975)
        )
        self.shake_fraction = float(
            params.get("alns_shake_fraction", 0.2)
        )
        self.shake_stagnation_factor = float(
            params.get("alns_shake_stagnation_factor", 3.0)
        )
        self.large_q_probability = float(
            params.get("alns_large_q_probability", 0.2)
        )
        self.q_low_divisor = max(2, int(params.get("alns_q_low_divisor", 20)))
        self.q_high_divisor = max(2, int(params.get("alns_q_high_divisor", 8)))
        self.large_q_low_divisor = max(
            2, int(params.get("alns_large_q_low_divisor", 8))
        )
        self.large_q_high_divisor = max(
            2, int(params.get("alns_large_q_high_divisor", 4))
        )
        self.shake_temperature_ratio = float(
            params.get("alns_shake_temperature_ratio", 0.8)
        )
        self.weight_floor = float(params.get("alns_weight_floor", 0.25))
        self.base_start_minute = int(
            params.get("alns_base_start_minute", WORK_DAY_START_MIN)
        )
        self.iteration_limit = int(
            params.get("alns_iteration_limit", 0)
        )
        self.acceptance = str(
            params.get("alns_acceptance", "sa")
        ).lower()
        self.lahc_length = max(
            10, int(params.get("alns_lahc_length", 500))
        )
        for route in self.routes:
            route.start_minute = self.base_start_minute

        destroy_weights = params.get("alns_destroy_weights")
        if (
            isinstance(destroy_weights, (list, tuple))
            and len(destroy_weights) == 7
        ):
            self.destroy_weights = [float(value) for value in destroy_weights]
        else:
            self.destroy_weights = [1.0, 1.0, 1.0, 0.6, 1.0, 1.0, 0.8]

        repair_weights = params.get("alns_repair_weights")
        if (
            isinstance(repair_weights, (list, tuple))
            and len(repair_weights) == 3
        ):
            self.repair_weights = [float(value) for value in repair_weights]
        else:
            self.repair_weights = [2.0, 1.0, 1.0]

        self.vehicle_by_type: Dict[str, Vehicle] = {}
        for route in routes:
            self.vehicle_by_type.setdefault(route.vehicle.vehicle_type, route.vehicle)
        for vehicle in available:
            self.vehicle_by_type.setdefault(vehicle.vehicle_type, vehicle)
        for vehicle_type, config in vehicle_config.items():
            if vehicle_type not in self.vehicle_by_type:
                fuel = float(config.get("fuel_per_100km", 12.0))
                fuel_empty_value = config.get("fuel_empty_per_100km")
                fuel_full_value = config.get("fuel_full_per_100km")
                fuel_empty = (
                    float(fuel_empty_value)
                    if fuel_empty_value is not None
                    else fuel * FUEL_EMPTY_LOAD_RATIO
                )
                fuel_full = (
                    float(fuel_full_value)
                    if fuel_full_value is not None
                    else fuel * FUEL_FULL_LOAD_RATIO
                )
                self.vehicle_by_type[vehicle_type] = Vehicle(
                    vehicle_id=-1,
                    vehicle_type=vehicle_type,
                    capacity=max(float(config.get("capacity", 1.0)), 1.0),
                    fixed_cost=float(config.get("fixed_cost", 0.0)),
                    speed_kmh=max(float(config.get("speed_kmh", 40.0)), 1.0),
                    fuel_per_100km=max(fuel, 0.0),
                    fuel_empty_per_100km=max(fuel_empty, 0.0),
                    fuel_full_per_100km=max(fuel_full, 0.0),
                    color=str(config.get("color", "#1f77b4")),
                )

        self.customer_by_id: Dict[int, Dict[str, Any]] = {}
        for route in routes:
            for customer in route.customers:
                self.customer_by_id[int(customer["customer_id"])] = customer

        self.index_by_id = {
            customer_id: index + 1
            for index, customer_id in enumerate(self.customer_by_id.keys())
        }
        self.info_by_id: Dict[int, Tuple[int, float, float, float, float]] = {}
        for customer_id, customer in self.customer_by_id.items():
            self.info_by_id[customer_id] = (
                self.index_by_id[customer_id],
                float(customer.get("demand", 0) or 0),
                float(customer.get("tw_earliest", 0) or 0),
                float(
                    customer.get("tw_latest", WORK_DAY_END_MIN)
                    or WORK_DAY_END_MIN
                ),
                float(
                    customer.get("service_time", customer.get("service_time_min", 0))
                    or 0
                ),
            )
        self.locations = [
            (float(self.depot["lat"]), float(self.depot["lon"]))
        ] + [
            (float(customer["lat"]), float(customer["lon"]))
            for customer in self.customer_by_id.values()
        ]
        location_count = len(self.locations)
        self.distances = [[0.0] * location_count for _ in range(location_count)]
        for left in range(location_count):
            for right in range(left + 1, location_count):
                distance = haversine_distance(
                    self.locations[left][0],
                    self.locations[left][1],
                    self.locations[right][0],
                    self.locations[right][1],
                )
                self.distances[left][right] = distance
                self.distances[right][left] = distance
        self._deadline = INF

        @lru_cache(maxsize=200_000)
        def evaluate(
            vehicle_type: str,
            customer_ids: Tuple[int, ...],
            start_minute: Optional[int] = None,
        ) -> RouteMetrics:
            return self._evaluate_route(
                vehicle_type, customer_ids, start_minute
            )

        self._evaluate = evaluate

    def _evaluate_route(
        self,
        vehicle_type: str,
        customer_ids: Tuple[int, ...],
        start_minute: Optional[int] = None,
    ) -> RouteMetrics:
        if start_minute is None:
            start_minute = self.base_start_minute
        if not customer_ids:
            return RouteMetrics(0.0, 0.0, 0.0, 0, 0.0, 0.0, 0.0)

        vehicle = self.vehicle_by_type[vehicle_type]
        total_demand = 0.0
        for cid in customer_ids:
            total_demand += self.info_by_id[cid][1]
        capacity = vehicle.capacity
        if total_demand > capacity + 1e-9:
            return RouteMetrics(INF, 0.0, 0.0, 0, 0.0, 0.0, 0.0)

        load = total_demand
        clock = start_minute
        previous_index = 0
        distance = 0.0
        fuel_liters = 0.0
        late_total = 0.0
        driving = 0.0
        waiting = 0.0
        service = 0.0
        empty_fuel = vehicle.fuel_empty_per_100km
        fuel_range = vehicle.fuel_full_per_100km - empty_fuel
        speed_kmh = vehicle.speed_kmh

        for cid in customer_ids:
            customer_index, demand, earliest, latest, service_time = (
                self.info_by_id[cid]
            )
            leg_km = self.distances[previous_index][customer_index]
            travel_min = travel_time_minutes(leg_km, clock, speed_kmh)
            fuel_per_100km = (
                empty_fuel + fuel_range * (load / capacity)
            ) * fuel_speed_factor(speed_multiplier(clock))
            fuel_liters += leg_km / 100.0 * fuel_per_100km

            arrival = clock + travel_min
            if arrival < earliest:
                waiting += earliest - arrival
                service_start = earliest
            else:
                service_start = arrival
            if service_start > latest:
                late_total += service_start - latest

            distance += leg_km
            driving += travel_min
            service += service_time
            clock = service_start + service_time
            load -= demand
            if load < 0.0:
                load = 0.0
            previous_index = customer_index

        leg_km = self.distances[previous_index][0]
        travel_min = travel_time_minutes(leg_km, clock, speed_kmh)
        return_time = clock + travel_min
        if return_time > WORK_DAY_END_MIN + 1e-9:
            return RouteMetrics(INF, 0.0, 0.0, 0, 0.0, 0.0, 0.0)

        distance += leg_km
        driving += travel_min
        fuel_liters += (
            leg_km
            / 100.0
            * empty_fuel
            * fuel_speed_factor(speed_multiplier(clock))
        )

        transport_cost = fuel_liters * self.fuel_price
        carbon_cost = fuel_liters * DIESEL_CO2_FACTOR * self.carbon_price
        labor_cost = (driving + waiting + service) / 60.0 * self.hourly_wage
        penalty_cost = late_total * self.late_penalty
        total_cost = (
            transport_cost
            + carbon_cost
            + vehicle.fixed_cost
            + labor_cost
            + penalty_cost
        )
        return RouteMetrics(
            cost=total_cost,
            distance_km=distance,
            fuel_liters=fuel_liters,
            late_minutes=int(round(late_total)),
            driving_min=driving,
            waiting_min=waiting,
            service_min=service,
        )

    def route_cost(self, route: RouteState) -> float:
        if not route.customers:
            return 0.0
        ids = tuple(int(customer["customer_id"]) for customer in route.customers)
        return self._evaluate(
            route.vehicle.vehicle_type, ids, route.start_minute
        ).cost

    def _record_pool(self, routes: Sequence[RouteState]) -> None:
        """记录优质路线，供集合划分重组合使用。"""
        for route in routes:
            if not route.customers:
                continue
            ids = tuple(int(customer["customer_id"]) for customer in route.customers)
            key = (route.vehicle.vehicle_type, tuple(sorted(ids)))
            metrics = self._evaluate(
                route.vehicle.vehicle_type, ids, route.start_minute
            )
            if not math.isfinite(metrics.cost):
                continue
            existing = self.route_pool.get(key)
            if existing is None or metrics.cost < existing[1].cost:
                self.route_pool[key] = (
                    ids,
                    metrics,
                    route.start_minute,
                )

    def solution_cost(self) -> float:
        return sum(self.route_cost(route) for route in self.routes)

    def _clone(self) -> Tuple[List[RouteState], List[Vehicle]]:
        return (
            [
                RouteState(
                    route.vehicle,
                    list(route.customers),
                    route.start_minute,
                )
                for route in self.routes
            ],
            list(self.available),
        )

    def _restore(
        self, routes: List[RouteState], available: List[Vehicle]
    ) -> None:
        self.routes = routes
        self.available = available

    def _cleanup(self) -> None:
        kept: List[RouteState] = []
        for route in self.routes:
            if route.customers:
                kept.append(route)
            else:
                self.available.append(route.vehicle)
        self.routes = kept

    def _remove_ids(self, ids: Sequence[int]) -> List[Dict[str, Any]]:
        remove_set = {int(cid) for cid in ids}
        removed: List[Dict[str, Any]] = []
        for route in self.routes:
            kept_customers = []
            for customer in route.customers:
                cid = int(customer["customer_id"])
                if cid in remove_set:
                    removed.append(customer)
                else:
                    kept_customers.append(customer)
            route.customers = kept_customers
        self._cleanup()
        return removed

    def destroy_random(self, q: int) -> List[Dict[str, Any]]:
        all_ids = list(self.customer_by_id.keys())
        q = min(q, len(all_ids))
        ids = self.rng.sample(all_ids, q)
        return self._remove_ids(ids)

    def destroy_worst(self, q: int) -> List[Dict[str, Any]]:
        savings: List[Tuple[float, int]] = []
        for route in self.routes:
            if time.perf_counter() > self._deadline:
                return []
            if len(route.customers) <= 1:
                current = self.route_cost(route)
                savings.append((current, int(route.customers[0]["customer_id"])))
                continue
            current = self.route_cost(route)
            ids = [int(customer["customer_id"]) for customer in route.customers]
            for index, cid in enumerate(ids):
                if time.perf_counter() > self._deadline:
                    return []
                candidate = ids[:index] + ids[index + 1 :]
                without = self._evaluate(route.vehicle.vehicle_type, tuple(candidate), route.start_minute).cost
                if without < INF:
                    savings.append((current - without, cid))
        savings.sort(reverse=True)
        candidates = savings[: max(q * 2, q)]
        selected = self.rng.sample(candidates, min(q, len(candidates)))
        return self._remove_ids([cid for _, cid in selected])

    def destroy_related(self, q: int) -> List[Dict[str, Any]]:
        all_ids = list(self.customer_by_id.keys())
        if not all_ids:
            return []
        seed = self.customer_by_id[self.rng.choice(all_ids)]

        def relatedness(cid: int) -> float:
            customer = self.customer_by_id[cid]
            distance = haversine_distance(
                seed["lat"], seed["lon"], customer["lat"], customer["lon"]
            )
            tw_gap = abs(
                float(seed.get("tw_earliest", 0) or 0)
                - float(customer.get("tw_earliest", 0) or 0)
            )
            demand_gap = abs(
                float(seed.get("demand", 0) or 0)
                - float(customer.get("demand", 0) or 0)
            )
            return distance + tw_gap * 0.05 + demand_gap * 0.1

        ranked = sorted(all_ids, key=relatedness)
        selected = ranked[: min(q, len(ranked))]
        return self._remove_ids(selected)

    def destroy_route(self, q: int) -> List[Dict[str, Any]]:
        if not self.routes:
            return []
        route = self.rng.choice(self.routes)
        ids = [int(customer["customer_id"]) for customer in route.customers]
        return self._remove_ids(ids)

    def destroy_small_route(self, q: int) -> List[Dict[str, Any]]:
        """优先移除装载量最小的路线，为削减车队规模创造机会。"""
        if not self.routes:
            return []
        ordered = sorted(
            self.routes,
            key=lambda route: sum(
                self.info_by_id[int(customer["customer_id"])][1]
                for customer in route.customers
            ),
        )
        pool = ordered[: max(1, len(ordered) // 2)]
        route = self.rng.choice(pool)
        ids = [int(customer["customer_id"]) for customer in route.customers]
        return self._remove_ids(ids)

    def destroy_segment(self, q: int) -> List[Dict[str, Any]]:
        """移除某条路线中的连续客户段，便于重组路线内部顺序。"""
        if not self.routes:
            return []
        route = self.rng.choice(self.routes)
        ids = [int(customer["customer_id"]) for customer in route.customers]
        if len(ids) <= 1:
            return self._remove_ids(ids)
        length = self.rng.randint(2, min(len(ids), max(2, q)))
        start = self.rng.randint(0, len(ids) - length)
        return self._remove_ids(ids[start : start + length])

    def destroy_route_pair(self, q: int) -> List[Dict[str, Any]]:
        """移除两条地理上最接近的路线，允许重新聚类。"""
        if len(self.routes) < 2:
            return self.destroy_route(q)

        centroids = []
        for route in self.routes:
            count = len(route.customers)
            if count == 0:
                centroids.append((0.0, 0.0))
                continue
            lat = sum(float(c["lat"]) for c in route.customers) / count
            lon = sum(float(c["lon"]) for c in route.customers) / count
            centroids.append((lat, lon))

        seed_index = self.rng.randrange(len(self.routes))
        seed_lat, seed_lon = centroids[seed_index]
        nearest_index = -1
        nearest_distance = INF
        for index, (lat, lon) in enumerate(centroids):
            if index == seed_index:
                continue
            distance = (lat - seed_lat) ** 2 + (lon - seed_lon) ** 2
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_index = index
        if nearest_index < 0:
            return self.destroy_route(q)

        ids = [
            int(customer["customer_id"])
            for index in (seed_index, nearest_index)
            for customer in self.routes[index].customers
        ]
        return self._remove_ids(ids)

    def _insertion_candidates(
        self, customer: Dict[str, Any]
    ) -> List[Tuple[float, Optional[int], int, Optional[Vehicle]]]:
        cid = int(customer["customer_id"])
        demand = float(customer.get("demand", 0) or 0)
        candidates: List[Tuple[float, Optional[int], int, Optional[Vehicle]]] = []

        for route_index, route in enumerate(self.routes):
            current_load = sum(
                float(c.get("demand", 0) or 0) for c in route.customers
            )
            if current_load + demand > route.vehicle.capacity + 1e-9:
                continue
            current_cost = self.route_cost(route)
            ids = [int(c["customer_id"]) for c in route.customers]
            for position in range(len(ids) + 1):
                sequence = ids[:position] + [cid] + ids[position:]
                metrics = self._evaluate(route.vehicle.vehicle_type, tuple(sequence))
                if metrics.cost < INF:
                    candidates.append(
                        (metrics.cost - current_cost, route_index, position, None)
                    )

        seen_types = set()
        for vehicle in self.available:
            if vehicle.vehicle_type in seen_types:
                continue
            seen_types.add(vehicle.vehicle_type)
            if demand > vehicle.capacity + 1e-9:
                continue
            metrics = self._evaluate(vehicle.vehicle_type, (cid,))
            if metrics.cost < INF:
                candidates.append((metrics.cost, None, 0, vehicle))

        candidates.sort(key=lambda item: item[0])
        return candidates

    def _apply_insertion(
        self,
        customer: Dict[str, Any],
        candidate: Tuple[float, Optional[int], int, Optional[Vehicle]],
    ) -> None:
        _, route_index, position, vehicle = candidate
        if route_index is not None:
            self.routes[route_index].customers.insert(position, customer)
            return
        if vehicle is None:
            return
        self.available = [
            candidate_vehicle
            for candidate_vehicle in self.available
            if candidate_vehicle.vehicle_id != vehicle.vehicle_id
        ]
        self.routes.append(
            RouteState(
                vehicle=vehicle,
                customers=[customer],
                start_minute=self.base_start_minute,
            )
        )

    def repair_greedy(self, removed: List[Dict[str, Any]]) -> bool:
        pending = list(removed)
        self.rng.shuffle(pending)
        for customer in pending:
            if time.perf_counter() > self._deadline:
                return False
            candidates = self._insertion_candidates(customer)
            if not candidates:
                return False
            self._apply_insertion(customer, candidates[0])
        return True

    def _repair_regret_k(self, removed: List[Dict[str, Any]], k: int) -> bool:
        pending = list(removed)
        while pending:
            if time.perf_counter() > self._deadline:
                return False
            best_customer = None
            best_candidate = None
            best_regret = -INF
            for customer in pending:
                if time.perf_counter() > self._deadline:
                    return False
                candidates = self._insertion_candidates(customer)
                if not candidates:
                    return False
                if len(candidates) == 1:
                    regret = INF
                else:
                    count = min(k, len(candidates))
                    regret = sum(
                        candidates[index][0] - candidates[0][0]
                        for index in range(1, count)
                    )
                if regret > best_regret:
                    best_regret = regret
                    best_customer = customer
                    best_candidate = candidates[0]
            if best_customer is None or best_candidate is None:
                return False
            self._apply_insertion(best_customer, best_candidate)
            pending.remove(best_customer)
        return True

    def repair_regret(self, removed: List[Dict[str, Any]]) -> bool:
        return self._repair_regret_k(removed, 2)

    def repair_regret3(self, removed: List[Dict[str, Any]]) -> bool:
        return self._repair_regret_k(removed, 3)

    def optimize_start_times(
        self,
        routes: Sequence[RouteState],
        step: int = 5,
        fine: bool = True,
    ) -> Dict[str, int]:
        """为每条路线选择使内部成本最低的出发时刻。"""
        start_times: Dict[str, int] = {}
        for route in routes:
            if not route.customers:
                continue
            ids = tuple(int(c["customer_id"]) for c in route.customers)
            best_start = route.start_minute
            best_route_cost = self._evaluate(
                route.vehicle.vehicle_type, ids, best_start
            ).cost
            for start in range(
                WORK_DAY_START_MIN, WORK_DAY_END_MIN, max(1, step)
            ):
                candidate_cost = self._evaluate(
                    route.vehicle.vehicle_type, ids, start
                ).cost
                if candidate_cost < best_route_cost - 1e-9:
                    best_route_cost = candidate_cost
                    best_start = start
            if fine:
                for start in range(
                    max(WORK_DAY_START_MIN, best_start - 4),
                    min(WORK_DAY_END_MIN - 1, best_start + 4) + 1,
                ):
                    candidate_cost = self._evaluate(
                        route.vehicle.vehicle_type, ids, start
                    ).cost
                    if candidate_cost < best_route_cost - 1e-9:
                        best_route_cost = candidate_cost
                        best_start = start
            route.start_minute = best_start
            start_times[route.vehicle.vehicle_type] = max(
                start_times.get(
                    route.vehicle.vehicle_type, WORK_DAY_START_MIN
                ),
                best_start,
            )
        return start_times

    def _polish_route(
        self, route: RouteState, max_passes: int = 8
    ) -> RouteState:
        """对单条路线做 2-opt / relocate / swap 的首次改进局部搜索。"""
        if len(route.customers) < 3:
            return route

        vehicle_type = route.vehicle.vehicle_type
        start_minute = route.start_minute
        ids = [int(customer["customer_id"]) for customer in route.customers]
        original_ids = list(ids)
        current_cost = self._evaluate(
            vehicle_type, tuple(ids), start_minute
        ).cost
        if not math.isfinite(current_cost):
            return route

        for _ in range(max_passes):
            improved = False
            n = len(ids)

            for i in range(n - 1):
                if time.perf_counter() > self._deadline:
                    break
                for j in range(i + 2, n + 1):
                    candidate = ids[:i] + ids[i:j][::-1] + ids[j:]
                    candidate_cost = self._evaluate(
                        vehicle_type, tuple(candidate), start_minute
                    ).cost
                    if candidate_cost < current_cost - 1e-9:
                        ids = candidate
                        current_cost = candidate_cost
                        improved = True
                        break
                if improved:
                    break
            if improved:
                continue

            for i in range(n):
                if time.perf_counter() > self._deadline:
                    break
                for j in range(n):
                    if i == j:
                        continue
                    candidate = ids.copy()
                    customer_id = candidate.pop(i)
                    candidate.insert(j, customer_id)
                    candidate_cost = self._evaluate(
                        vehicle_type, tuple(candidate), start_minute
                    ).cost
                    if candidate_cost < current_cost - 1e-9:
                        ids = candidate
                        current_cost = candidate_cost
                        improved = True
                        break
                if improved:
                    break
            if improved:
                continue

            for segment_length in (2, 3):
                if improved or len(ids) <= segment_length:
                    break
                for i in range(n - segment_length + 1):
                    if time.perf_counter() > self._deadline:
                        break
                    segment = ids[i : i + segment_length]
                    remainder = ids[:i] + ids[i + segment_length :]
                    for position in range(len(remainder) + 1):
                        candidate = (
                            remainder[:position]
                            + segment
                            + remainder[position:]
                        )
                        candidate_cost = self._evaluate(
                            vehicle_type, tuple(candidate), start_minute
                        ).cost
                        if candidate_cost < current_cost - 1e-9:
                            ids = candidate
                            current_cost = candidate_cost
                            improved = True
                            break
                    if improved:
                        break
            if improved:
                continue

            for i in range(n - 1):
                if time.perf_counter() > self._deadline:
                    break
                for j in range(i + 1, n):
                    candidate = ids.copy()
                    candidate[i], candidate[j] = candidate[j], candidate[i]
                    candidate_cost = self._evaluate(
                        vehicle_type, tuple(candidate), start_minute
                    ).cost
                    if candidate_cost < current_cost - 1e-9:
                        ids = candidate
                        current_cost = candidate_cost
                        improved = True
                        break
                if improved:
                    break
            if not improved:
                break

        if ids == original_ids:
            return route
        return RouteState(
            vehicle=route.vehicle,
            customers=[self.customer_by_id[cid] for cid in ids],
            start_minute=start_minute,
        )

    def _eliminate_routes(
        self,
        routes: List[RouteState],
        current_cost: float,
    ) -> Tuple[List[RouteState], float]:
        """尝试整条路线消除：把客户并入其余路线以削减固定成本。"""
        if len(routes) <= 1:
            return routes, current_cost

        while time.perf_counter() < self._deadline and len(routes) > 1:
            ordered = sorted(
                routes,
                key=lambda route: sum(
                    self.info_by_id[int(customer["customer_id"])][1]
                    for customer in route.customers
                ),
            )
            accepted = False
            for target in ordered:
                if time.perf_counter() > self._deadline:
                    break
                removed = list(target.customers)
                remaining = [
                    RouteState(
                        route.vehicle,
                        list(route.customers),
                        route.start_minute,
                    )
                    for route in routes
                    if route is not target
                ]
                saved_routes = self.routes
                saved_available = self.available
                self.routes = remaining
                self.available = []
                inserted = self.repair_regret(removed)
                if inserted:
                    self._cleanup()
                    polished = [
                        self._polish_route(route, max_passes=3)
                        for route in self.routes
                    ]
                    candidate_cost = sum(
                        self.route_cost(route) for route in polished
                    )
                    if candidate_cost < current_cost - 1e-9:
                        routes = polished
                        current_cost = candidate_cost
                        accepted = True
                        break
                self.routes = saved_routes
                self.available = saved_available
            if not accepted:
                break
        return routes, current_cost

    def two_opt_star(
        self,
        routes: List[RouteState],
        time_limit: float = 15.0,
    ) -> int:
        """跨路线 2-opt* 尾部交换，按完整五维成本择优。"""
        deadline = time.perf_counter() + max(0.1, time_limit)
        moves = 0
        while time.perf_counter() < deadline:
            improved = False
            for a_index in range(len(routes)):
                if time.perf_counter() >= deadline:
                    break
                route_a = routes[a_index]
                ids_a = [
                    int(c["customer_id"]) for c in route_a.customers
                ]
                prefix_a = [0.0]
                for cid in ids_a:
                    prefix_a.append(prefix_a[-1] + self.info_by_id[cid][1])
                total_a = prefix_a[-1]
                cap_a = route_a.vehicle.capacity

                for b_index in range(a_index + 1, len(routes)):
                    if time.perf_counter() >= deadline:
                        break
                    route_b = routes[b_index]
                    ids_b = [
                        int(c["customer_id"]) for c in route_b.customers
                    ]
                    prefix_b = [0.0]
                    for cid in ids_b:
                        prefix_b.append(
                            prefix_b[-1] + self.info_by_id[cid][1]
                        )
                    total_b = prefix_b[-1]
                    cap_b = route_b.vehicle.capacity
                    old_cost = self.route_cost(route_a) + self.route_cost(
                        route_b
                    )

                    best: Optional[
                        Tuple[float, int, int, List[int], List[int]]
                    ] = None
                    for i in range(len(ids_a) + 1):
                        for j in range(len(ids_b) + 1):
                            if (i == 0 and j == 0) or (
                                i == len(ids_a) and j == len(ids_b)
                            ):
                                continue
                            new_ids_a = ids_a[:i] + ids_b[j:]
                            new_ids_b = ids_b[:j] + ids_a[i:]
                            if not new_ids_a or not new_ids_b:
                                continue
                            load_a = prefix_a[i] + (
                                total_b - prefix_b[j]
                            )
                            load_b = prefix_b[j] + (
                                total_a - prefix_a[i]
                            )
                            if (
                                load_a > cap_a + 1e-9
                                or load_b > cap_b + 1e-9
                            ):
                                continue
                            cost_a = self._evaluate(
                                route_a.vehicle.vehicle_type,
                                tuple(new_ids_a),
                                route_a.start_minute,
                            ).cost
                            if cost_a >= INF:
                                continue
                            cost_b = self._evaluate(
                                route_b.vehicle.vehicle_type,
                                tuple(new_ids_b),
                                route_b.start_minute,
                            ).cost
                            total = cost_a + cost_b
                            if total < old_cost - 1e-9 and (
                                best is None or total < best[0]
                            ):
                                best = (
                                    total,
                                    i,
                                    j,
                                    new_ids_a,
                                    new_ids_b,
                                )

                    if best is not None:
                        _, i, j, new_ids_a, new_ids_b = best
                        routes[a_index] = RouteState(
                            route_a.vehicle,
                            [
                                self.customer_by_id[cid]
                                for cid in new_ids_a
                            ],
                            start_minute=route_a.start_minute,
                        )
                        routes[b_index] = RouteState(
                            route_b.vehicle,
                            [
                                self.customer_by_id[cid]
                                for cid in new_ids_b
                            ],
                            start_minute=route_b.start_minute,
                        )
                        self.optimize_start_times(
                            [routes[a_index], routes[b_index]]
                        )
                        moves += 1
                        improved = True
                        break
                if improved:
                    break
            if not improved:
                break
        if moves:
            self.optimize_start_times(routes)
        return moves

    def inter_route_vnd(
        self,
        routes: List[RouteState],
        time_limit: float = 15.0,
    ) -> int:
        """跨路线单客户搬移/交换的首次改进局部搜索。"""
        deadline = time.perf_counter() + max(0.1, time_limit)
        moves = 0
        while time.perf_counter() < deadline:
            improved = False

            # 单客户搬移
            for a_index in range(len(routes)):
                if time.perf_counter() >= deadline:
                    break
                route_a = routes[a_index]
                ids_a = [int(c["customer_id"]) for c in route_a.customers]
                load_a = sum(self.info_by_id[cid][1] for cid in ids_a)
                cap_a = route_a.vehicle.capacity
                for b_index in range(len(routes)):
                    if a_index == b_index:
                        continue
                    route_b = routes[b_index]
                    ids_b = [int(c["customer_id"]) for c in route_b.customers]
                    load_b = sum(self.info_by_id[cid][1] for cid in ids_b)
                    cap_b = route_b.vehicle.capacity
                    current = self.route_cost(route_a) + self.route_cost(
                        route_b
                    )
                    for position in range(len(ids_a)):
                        if time.perf_counter() >= deadline:
                            break
                        cid = ids_a[position]
                        demand = self.info_by_id[cid][1]
                        if load_b + demand > cap_b + 1e-9:
                            continue
                        remaining_ids = (
                            ids_a[:position] + ids_a[position + 1 :]
                        )
                        cost_a = self._evaluate(
                            route_a.vehicle.vehicle_type,
                            tuple(remaining_ids) if remaining_ids else (),
                            route_a.start_minute,
                        ).cost
                        if cost_a >= INF:
                            continue
                        for insert_pos in range(len(ids_b) + 1):
                            new_b_ids = (
                                ids_b[:insert_pos]
                                + [cid]
                                + ids_b[insert_pos:]
                            )
                            cost_b = self._evaluate(
                                route_b.vehicle.vehicle_type,
                                tuple(new_b_ids),
                                route_b.start_minute,
                            ).cost
                            if cost_b >= INF:
                                continue
                            if cost_a + cost_b < current - 1e-9:
                                routes[a_index] = RouteState(
                                    route_a.vehicle,
                                    [
                                        self.customer_by_id[item]
                                        for item in remaining_ids
                                    ],
                                    start_minute=route_a.start_minute,
                                )
                                routes[b_index] = RouteState(
                                    route_b.vehicle,
                                    [
                                        self.customer_by_id[item]
                                        for item in new_b_ids
                                    ],
                                    start_minute=route_b.start_minute,
                                )
                                self.optimize_start_times(
                                    [routes[a_index], routes[b_index]]
                                )
                                moves += 1
                                improved = True
                                break
                        if improved:
                            break
                    if improved:
                        break
                if improved:
                    break
            if improved:
                continue

            # 单客户交换
            for a_index in range(len(routes)):
                if time.perf_counter() >= deadline:
                    break
                route_a = routes[a_index]
                ids_a = [int(c["customer_id"]) for c in route_a.customers]
                load_a = sum(self.info_by_id[cid][1] for cid in ids_a)
                cap_a = route_a.vehicle.capacity
                for b_index in range(a_index + 1, len(routes)):
                    route_b = routes[b_index]
                    ids_b = [int(c["customer_id"]) for c in route_b.customers]
                    load_b = sum(self.info_by_id[cid][1] for cid in ids_b)
                    cap_b = route_b.vehicle.capacity
                    current = self.route_cost(route_a) + self.route_cost(
                        route_b
                    )
                    for i, cid_a in enumerate(ids_a):
                        if time.perf_counter() >= deadline:
                            break
                        demand_a = self.info_by_id[cid_a][1]
                        for j, cid_b in enumerate(ids_b):
                            demand_b = self.info_by_id[cid_b][1]
                            if (
                                load_a - demand_a + demand_b > cap_a + 1e-9
                                or load_b - demand_b + demand_a
                                > cap_b + 1e-9
                            ):
                                continue
                            new_a_ids = list(ids_a)
                            new_b_ids = list(ids_b)
                            new_a_ids[i] = cid_b
                            new_b_ids[j] = cid_a
                            cost_a = self._evaluate(
                                route_a.vehicle.vehicle_type,
                                tuple(new_a_ids),
                                route_a.start_minute,
                            ).cost
                            cost_b = self._evaluate(
                                route_b.vehicle.vehicle_type,
                                tuple(new_b_ids),
                                route_b.start_minute,
                            ).cost
                            if cost_a + cost_b < current - 1e-9:
                                routes[a_index] = RouteState(
                                    route_a.vehicle,
                                    [
                                        self.customer_by_id[item]
                                        for item in new_a_ids
                                    ],
                                    start_minute=route_a.start_minute,
                                )
                                routes[b_index] = RouteState(
                                    route_b.vehicle,
                                    [
                                        self.customer_by_id[item]
                                        for item in new_b_ids
                                    ],
                                    start_minute=route_b.start_minute,
                                )
                                self.optimize_start_times(
                                    [routes[a_index], routes[b_index]]
                                )
                                moves += 1
                                improved = True
                                break
                        if improved:
                            break
                    if improved:
                        break
                if improved:
                    break
            if not improved:
                break
        if moves:
            self.optimize_start_times(routes)
        return moves

    def inter_route_segment_vnd(
        self,
        routes: List[RouteState],
        time_limit: float = 15.0,
    ) -> int:
        """跨路线连续客户段（2-3 个）搬移的首次改进搜索。"""
        deadline = time.perf_counter() + max(0.1, time_limit)
        moves = 0
        while time.perf_counter() < deadline:
            improved = False
            for a_index in range(len(routes)):
                if time.perf_counter() >= deadline:
                    break
                route_a = routes[a_index]
                ids_a = [int(c["customer_id"]) for c in route_a.customers]
                load_a = sum(self.info_by_id[cid][1] for cid in ids_a)
                for b_index in range(len(routes)):
                    if a_index == b_index:
                        continue
                    route_b = routes[b_index]
                    ids_b = [int(c["customer_id"]) for c in route_b.customers]
                    load_b = sum(self.info_by_id[cid][1] for cid in ids_b)
                    cap_b = route_b.vehicle.capacity
                    current = self.route_cost(route_a) + self.route_cost(
                        route_b
                    )
                    for segment_length in (2, 3):
                        if improved or len(ids_a) <= segment_length:
                            break
                        for start in range(
                            len(ids_a) - segment_length + 1
                        ):
                            if time.perf_counter() >= deadline:
                                break
                            segment = ids_a[start : start + segment_length]
                            segment_demand = sum(
                                self.info_by_id[cid][1] for cid in segment
                            )
                            if load_b + segment_demand > cap_b + 1e-9:
                                continue
                            remaining_ids = (
                                ids_a[:start]
                                + ids_a[start + segment_length :]
                            )
                            if not remaining_ids:
                                continue
                            cost_a = self._evaluate(
                                route_a.vehicle.vehicle_type,
                                tuple(remaining_ids),
                                route_a.start_minute,
                            ).cost
                            if cost_a >= INF:
                                continue
                            for insert_pos in range(len(ids_b) + 1):
                                new_b_ids = (
                                    ids_b[:insert_pos]
                                    + segment
                                    + ids_b[insert_pos:]
                                )
                                cost_b = self._evaluate(
                                    route_b.vehicle.vehicle_type,
                                    tuple(new_b_ids),
                                    route_b.start_minute,
                                ).cost
                                if cost_b >= INF:
                                    continue
                                if cost_a + cost_b < current - 1e-9:
                                    routes[a_index] = RouteState(
                                        route_a.vehicle,
                                        [
                                            self.customer_by_id[item]
                                            for item in remaining_ids
                                        ],
                                        start_minute=route_a.start_minute,
                                    )
                                    routes[b_index] = RouteState(
                                        route_b.vehicle,
                                        [
                                            self.customer_by_id[item]
                                            for item in new_b_ids
                                        ],
                                        start_minute=route_b.start_minute,
                                    )
                                    self.optimize_start_times(
                                        [
                                            routes[a_index],
                                            routes[b_index],
                                        ]
                                    )
                                    moves += 1
                                    improved = True
                                    break
                            if improved:
                                break
                        if improved:
                            break
                    if improved:
                        break
                if improved:
                    break
            if not improved:
                break
        if moves:
            self.optimize_start_times(routes)
        return moves

    def pairwise_alns(
        self,
        routes: List[RouteState],
        iterations_per_pair: int = 400,
    ) -> int:
        """对每一对路线运行小规模 ALNS 重优化。"""
        moves = 0
        for a_index in range(len(routes)):
            if not routes[a_index].customers:
                continue
            for b_index in range(a_index + 1, len(routes)):
                if not routes[b_index].customers:
                    continue
                route_a = routes[a_index]
                route_b = routes[b_index]
                counts: Dict[str, int] = {}
                for route in (route_a, route_b):
                    counts[route.vehicle.vehicle_type] = (
                        counts.get(route.vehicle.vehicle_type, 0) + 1
                    )
                pair_config: Dict[str, Dict[str, Any]] = {}
                for vehicle_type, count in counts.items():
                    vehicle = (
                        route_a.vehicle
                        if route_a.vehicle.vehicle_type == vehicle_type
                        else route_b.vehicle
                    )
                    pair_config[vehicle_type] = {
                        "capacity": vehicle.capacity,
                        "fixed_cost": vehicle.fixed_cost,
                        "fuel_per_100km": vehicle.fuel_per_100km,
                        "fuel_empty_per_100km": vehicle.fuel_empty_per_100km,
                        "fuel_full_per_100km": vehicle.fuel_full_per_100km,
                        "speed_kmh": vehicle.speed_kmh,
                        "count": count,
                        "color": vehicle.color,
                    }

                old_cost = self.route_cost(route_a) + self.route_cost(
                    route_b
                )
                pair_params = {
                    **self.params,
                    "alns_iteration_limit": max(
                        100, int(iterations_per_pair)
                    ),
                    "alns_base_start_minute": min(
                        route_a.start_minute, route_b.start_minute
                    ),
                }
                pair_optimizer = _ALNSOptimizer(
                    [
                        RouteState(
                            route_a.vehicle,
                            list(route_a.customers),
                            route_a.start_minute,
                        ),
                        RouteState(
                            route_b.vehicle,
                            list(route_b.customers),
                            route_b.start_minute,
                        ),
                    ],
                    [],
                    self.depot,
                    pair_config,
                    pair_params,
                    1000 + a_index * 10 + b_index,
                )
                best_routes, _, best_cost, _ = pair_optimizer.run(5.0)
                if best_cost >= old_cost - 1e-9:
                    continue
                padded = list(best_routes)
                while len(padded) < 2:
                    padded.append(
                        RouteState(
                            route_a.vehicle,
                            [],
                            route_a.start_minute,
                        )
                    )
                routes[a_index] = padded[0]
                routes[b_index] = padded[1]
                moves += 1
        if moves:
            self.optimize_start_times(routes)
        return moves

    def _roulette(self, weights: Sequence[float]) -> int:
        total = sum(weights)
        if total <= 0:
            return 0
        point = self.rng.random() * total
        upto = 0.0
        for index, weight in enumerate(weights):
            upto += weight
            if point <= upto:
                return index
        return len(weights) - 1

    def run(
        self,
        time_limit: float,
        stats: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[RouteState], List[Vehicle], float, float]:
        initial_cost = self.solution_cost()
        if not math.isfinite(initial_cost):
            return self.routes, self.available, INF, 0.0
        self._record_pool(self.routes)

        current_cost = initial_cost
        best_routes, best_available = self._clone()
        best_cost = initial_cost
        temperature = max(1.0, initial_cost * self.temperature_ratio)

        destroy_ops = [
            self.destroy_random,
            self.destroy_worst,
            self.destroy_related,
            self.destroy_route,
            self.destroy_small_route,
            self.destroy_segment,
            self.destroy_route_pair,
        ]
        repair_ops = [self.repair_greedy, self.repair_regret, self.repair_regret3]
        destroy_weights = list(self.destroy_weights)
        repair_weights = list(self.repair_weights)
        destroy_scores = [0.0] * len(destroy_ops)
        destroy_uses = [0] * len(destroy_ops)
        destroy_totals = [0] * len(destroy_ops)
        repair_scores = [0.0] * len(repair_ops)
        repair_uses = [0] * len(repair_ops)
        repair_totals = [0] * len(repair_ops)

        started = time.perf_counter()
        if self.iteration_limit > 0:
            main_time = INF
            max_iterations = self.iteration_limit
            self._deadline = started + max(time_limit * 3.0, 180.0)
        else:
            main_time = max(0.1, time_limit * 0.8)
            max_iterations = 5000
            self._deadline = started + main_time
        iteration = 0
        accepted_count = 0
        improvement_count = 0
        best_iteration = 0
        stagnant = 0
        initial_temperature = temperature
        n = len(self.customer_by_id)
        stagnation_limit = max(
            150, int(n * self.shake_stagnation_factor)
        )
        shake_count = 0
        lahc_history = (
            [initial_cost] * self.lahc_length
            if self.acceptance == "lahc"
            else None
        )

        while iteration < max_iterations and (
            not math.isfinite(main_time)
            or time.perf_counter() - started < main_time
        ):
            elapsed = time.perf_counter() - started
            if math.isfinite(main_time) and elapsed > main_time * 1.05:
                break

            q_low = min(n, max(2, n // self.q_low_divisor))
            q_high = min(n, max(q_low, n // self.q_high_divisor))
            destroy_index = self._roulette(destroy_weights)
            if destroy_ops[destroy_index] in (
                self.destroy_route,
                self.destroy_small_route,
                self.destroy_route_pair,
            ):
                q = q_high
            elif self.rng.random() < self.large_q_probability:
                large_low = min(
                    n, max(3, n // self.large_q_low_divisor)
                )
                large_high = max(
                    large_low,
                    min(n, max(4, n // self.large_q_high_divisor)),
                )
                q = self.rng.randint(large_low, large_high)
            else:
                q = self.rng.randint(q_low, q_high)

            repair_index = self._roulette(repair_weights)
            backup_routes, backup_available = self._clone()
            before_cost = current_cost

            removed = destroy_ops[destroy_index](q)
            if not removed:
                self._restore(backup_routes, backup_available)
                iteration += 1
                continue

            repaired = repair_ops[repair_index](removed)
            if not repaired:
                self._restore(backup_routes, backup_available)
                iteration += 1
                continue

            new_cost = self.solution_cost()
            if not math.isfinite(new_cost):
                self._restore(backup_routes, backup_available)
                iteration += 1
                continue

            if lahc_history is not None:
                history_index = iteration % self.lahc_length
                accept = (
                    new_cost < current_cost
                    or new_cost <= lahc_history[history_index]
                )
                if accept and new_cost < lahc_history[history_index]:
                    lahc_history[history_index] = new_cost
            else:
                accept = new_cost < current_cost
                if not accept:
                    delta = new_cost - current_cost
                    accept = self.rng.random() < math.exp(
                        -delta / max(temperature, 1e-9)
                    )

            score = 0.0
            if accept:
                accepted_count += 1
                current_cost = new_cost
                if new_cost < best_cost:
                    best_cost = new_cost
                    best_routes, best_available = self._clone()
                    self._record_pool(best_routes)
                    best_iteration = iteration
                    improvement_count += 1
                    stagnant = 0
                    score = 6.0
                elif new_cost < before_cost:
                    score = 3.0
                else:
                    score = 1.0
            else:
                self._restore(backup_routes, backup_available)

            destroy_scores[destroy_index] += score
            destroy_uses[destroy_index] += 1
            destroy_totals[destroy_index] += 1
            repair_scores[repair_index] += score
            repair_uses[repair_index] += 1
            repair_totals[repair_index] += 1

            iteration += 1
            temperature *= self.cooling_factor
            stagnant += 1
            if stagnant >= stagnation_limit:
                saved_routes, saved_available = self._clone()
                self.routes = [
                    RouteState(
                        route.vehicle,
                        list(route.customers),
                        route.start_minute,
                    )
                    for route in best_routes
                ]
                self.available = list(best_available)
                removed = self.destroy_random(
                    max(8, int(n * self.shake_fraction))
                )
                if removed and self.repair_regret3(removed):
                    shaken_cost = self.solution_cost()
                    if math.isfinite(shaken_cost):
                        current_cost = shaken_cost
                        temperature = max(
                            temperature,
                            initial_temperature * self.shake_temperature_ratio,
                        )
                        shake_count += 1
                        stagnant = 0
                    else:
                        self._restore(saved_routes, saved_available)
                else:
                    self._restore(saved_routes, saved_available)
            elif stagnant >= max(150, n * 2):
                temperature = max(temperature, initial_temperature * 0.4)

            if iteration % 50 == 0:
                if iteration % 200 == 0:
                    self._record_pool(self.routes)
                for index in range(len(destroy_weights)):
                    if destroy_uses[index]:
                        destroy_weights[index] = max(
                            self.weight_floor,
                            0.7 * destroy_weights[index]
                            + 0.3 * destroy_scores[index] / destroy_uses[index],
                        )
                    destroy_scores[index] = 0.0
                    destroy_uses[index] = 0
                for index in range(len(repair_weights)):
                    if repair_uses[index]:
                        repair_weights[index] = max(
                            self.weight_floor,
                            0.7 * repair_weights[index]
                            + 0.3 * repair_scores[index] / repair_uses[index],
                        )
                    repair_scores[index] = 0.0
                    repair_uses[index] = 0

            if math.isfinite(main_time) and (
                time.perf_counter() - started >= main_time
            ):
                break

        polish_started = time.perf_counter()
        if self.iteration_limit > 0:
            self._deadline = INF
        else:
            polish_budget = max(0.2, min(20.0, time_limit * 0.2))
            self._deadline = polish_started + polish_budget
        polished_routes: List[RouteState] = []
        for route in best_routes:
            if time.perf_counter() > self._deadline:
                polished_routes.append(route)
                continue
            polished_routes.append(self._polish_route(route, max_passes=8))
        best_routes = polished_routes
        best_cost = sum(self.route_cost(route) for route in best_routes)
        eliminated_routes, eliminated_cost = self._eliminate_routes(
            best_routes, best_cost
        )
        if eliminated_cost < best_cost - 1e-9:
            best_routes = eliminated_routes
            best_cost = eliminated_cost
        self._record_pool(best_routes)

        elapsed = time.perf_counter() - started
        if stats is not None:
            stats.update(
                {
                    "iterations": iteration,
                    "accepted": accepted_count,
                    "improvements": improvement_count,
                    "best_iteration": best_iteration,
                    "initial_cost": initial_cost,
                    "best_cost": best_cost,
                    "elapsed_seconds": round(elapsed, 2),
                    "best_routes": len(best_routes),
                    "shakes": shake_count,
                    "destroy_totals": dict(zip(
                        [op.__name__ for op in destroy_ops], destroy_totals
                    )),
                    "repair_totals": dict(zip(
                        [op.__name__ for op in repair_ops], repair_totals
                    )),
                }
            )
        return best_routes, best_available, best_cost, elapsed


def _build_route_stops(
    route: RouteState,
    depot: Dict[str, Any],
) -> Dict[str, Any]:
    vehicle = route.vehicle
    depot_name = str(depot.get("customer_name") or depot.get("name") or "仓库")
    start_minute = int(route.start_minute)
    start_stop = {
        **copy.deepcopy(depot),
        "node": 0,
        "customer_id": 0,
        "customer_name": depot_name,
        "demand": 0,
        "service_time": 0,
        "raw_arrival_time": start_minute,
        "arrival_time": start_minute,
        "departure_time": start_minute,
        "late_minutes": 0,
        "is_late": False,
    }

    total_demand = sum(float(c.get("demand", 0) or 0) for c in route.customers)
    load = total_demand
    clock = start_minute
    previous = depot
    distance = 0.0
    late_total = 0.0
    stops: List[Dict[str, Any]] = [start_stop]

    for customer in route.customers:
        leg_km = haversine_distance(
            previous["lat"], previous["lon"], customer["lat"], customer["lon"]
        )
        travel_min = travel_time_minutes(leg_km, clock, vehicle.speed_kmh)
        arrival = clock + travel_min
        earliest = float(customer.get("tw_earliest", 0) or 0)
        latest = float(customer.get("tw_latest", WORK_DAY_END_MIN) or WORK_DAY_END_MIN)
        service_start = max(arrival, earliest)
        late = max(0.0, service_start - latest)
        service_time = float(
            customer.get("service_time", customer.get("service_time_min", 0)) or 0
        )
        departure = service_start + service_time
        customer_stop = {
            **copy.deepcopy(customer),
            "node": int(customer["customer_id"]),
            "customer_id": int(customer["customer_id"]),
            "service_time": service_time,
            "raw_arrival_time": int(round(arrival)),
            "arrival_time": int(round(service_start)),
            "departure_time": int(round(departure)),
            "late_minutes": int(round(late)),
            "is_late": late > 0,
        }
        stops.append(customer_stop)
        distance += leg_km
        late_total += late
        clock = departure
        load = max(0.0, load - float(customer.get("demand", 0) or 0))
        previous = customer

    return_leg = haversine_distance(
        previous["lat"], previous["lon"], depot["lat"], depot["lon"]
    )
    return_time = clock + travel_time_minutes(
        return_leg, clock, vehicle.speed_kmh
    )
    distance += return_leg
    return_stop = {
        **copy.deepcopy(depot),
        "node": 0,
        "customer_id": None,
        "customer_name": f"{depot_name} · 返程",
        "demand": 0,
        "service_time": 0,
        "raw_arrival_time": int(round(return_time)),
        "arrival_time": int(round(return_time)),
        "departure_time": int(round(return_time)),
        "late_minutes": 0,
        "is_late": False,
    }
    stops.append(return_stop)

    return {
        "vehicle_id": vehicle.vehicle_id,
        "vehicle_type": vehicle.vehicle_type,
        "vehicle_color": vehicle.color,
        "capacity": int(round(vehicle.capacity)),
        "stops": stops,
        "distance_km": round(distance, 2),
        "total_demand": int(round(total_demand)),
        "total_time_min": max(0, int(round(return_time - start_minute))),
        "late_minutes": int(round(late_total)),
    }


def _build_solution(
    routes: List[RouteState],
    vehicle_config: Dict[str, Dict[str, Any]],
    depot: Dict[str, Any],
    initial_solution: Dict[str, Any],
    alns_seconds: float,
) -> Dict[str, Any]:
    non_empty = [route for route in routes if route.customers]
    non_empty.sort(key=lambda route: route.vehicle.vehicle_id)
    route_dicts = [_build_route_stops(route, depot) for route in non_empty]

    vehicles_used: Dict[str, int] = {v_type: 0 for v_type in vehicle_config}
    for route in route_dicts:
        vehicle_type = route["vehicle_type"]
        vehicles_used[vehicle_type] = vehicles_used.get(vehicle_type, 0) + 1

    total_distance = sum(float(route["distance_km"]) for route in route_dicts)
    total_late = sum(int(route["late_minutes"]) for route in route_dicts)
    initial_time = float(initial_solution.get("solve_time_seconds", 0) or 0)

    result: Dict[str, Any] = {
        "routes": route_dicts,
        "total_distance": round(total_distance, 2),
        "vehicles_used": vehicles_used,
        "total_late_minutes": total_late,
        "solution_status": "SUCCESS",
        "solve_time_seconds": round(initial_time + alns_seconds, 2),
    }
    if "note" in initial_solution:
        result["note"] = initial_solution["note"]
    return result


def improve_solution_with_alns(
    solution: Dict[str, Any],
    vehicle_config: Dict[str, Dict[str, Any]],
    params: Optional[Dict[str, Any]] = None,
    time_limit: float = 3.0,
    seed: int = 42,
    stats: Optional[Dict[str, Any]] = None,
    recombine: bool = False,
    recombine_time: float = 5.0,
    route_pool_out: Optional[Dict[Any, Any]] = None,
) -> Dict[str, Any]:
    """Improve an OR-Tools solution with adaptive destroy/repair operators.

    The returned solution is the ALNS best solution when its internal
    objective improves.  The caller should compare the actual five-factor
    cost and keep the better of the two solutions.
    """
    if solution.get("solution_status") != "SUCCESS" or not solution.get("routes"):
        return solution
    if time_limit <= 0:
        return solution

    merged_params = {**DEFAULT_PARAMS, **(params or {})}
    pool = _build_vehicle_pool(vehicle_config)
    routes, available, depot = _extract_initial(solution, pool)
    if routes is None or available is None or depot is None:
        return solution

    optimizer = _ALNSOptimizer(
        routes, available, depot, vehicle_config, merged_params, seed
    )
    initial_cost = optimizer.solution_cost()
    best_routes, _best_available, best_cost, elapsed = optimizer.run(
        time_limit, stats=stats
    )

    recombine_seconds = 0.0
    recombined = False
    if recombine and optimizer.route_pool:
        from .recombine import recombine_route_pool

        recombine_started = time.perf_counter()
        result = recombine_route_pool(
            optimizer,
            time_limit=max(1.0, min(recombine_time, time_limit)),
        )
        if result is not None:
            combined_routes, combined_cost = result
            optimizer._deadline = time.perf_counter() + max(
                1.0, recombine_time
            )
            polished_routes = [
                optimizer._polish_route(route, max_passes=5)
                for route in combined_routes
            ]
            polished_cost = sum(
                optimizer.route_cost(route) for route in polished_routes
            )
            if polished_cost < combined_cost - 1e-9:
                combined_routes = polished_routes
                combined_cost = polished_cost
            if combined_cost < best_cost - 1e-9:
                best_routes = combined_routes
                best_cost = combined_cost
                recombined = True
        recombine_seconds = time.perf_counter() - recombine_started

    start_times = optimizer.optimize_start_times(best_routes)
    optimizer._deadline = time.perf_counter() + 5.0
    best_routes = [
        optimizer._polish_route(route, max_passes=4)
        for route in best_routes
        if route.customers
    ]
    start_times = optimizer.optimize_start_times(best_routes)
    best_cost = sum(optimizer.route_cost(route) for route in best_routes)
    optimizer._record_pool(best_routes)
    if route_pool_out is not None:
        for key, value in optimizer.route_pool.items():
            existing = route_pool_out.get(key)
            if existing is None or value[1].cost < existing[1].cost:
                route_pool_out[key] = value
    if stats is not None:
        stats["start_times"] = start_times
        stats["best_cost"] = best_cost

    if not math.isfinite(best_cost) or best_cost >= initial_cost - 1e-9:
        return solution

    if stats is not None:
        stats["recombined"] = recombined
        stats["pool_size"] = len(optimizer.route_pool)
        stats["recombine_seconds"] = round(recombine_seconds, 2)

    candidate = _build_solution(
        best_routes,
        vehicle_config,
        depot,
        solution,
        elapsed + recombine_seconds,
    )

    # Keep the original if the actual five-factor cost is not better.
    try:
        from core.cost import calculate_green_cost

        before_actual = calculate_green_cost(
            solution, vehicle_config, merged_params
        )["total_cost"]
        after_actual = calculate_green_cost(
            candidate, vehicle_config, merged_params
        )["total_cost"]
        if after_actual >= before_actual - 1e-6:
            return solution
    except Exception:
        pass
    return candidate
