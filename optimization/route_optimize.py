"""
2-opt 路线后处理优化器

对 OR-Tools 求解结果进行 2-opt 后处理，消除路径交叉并缩短总距离。

核心思想：
- 2-opt 交换：在一条路线中选取两个非相邻边 (i→j) 和 (k→l)，
  替换为 (i→k) 和 (j→l)（即反转 i~k 之间的访问顺序）。
- 如果新路线距离更短且满足时间窗约束，则接受交换。
- 重复直到无法改进为止。

约束保证：
- 时间窗：每次 2-opt 交换后重新计算到达时间，违反则回退
- 容量：同一路线的客户集合不变，容量约束天然满足

Example:
    >>> from optimization.route_optimize import post_process_solution
    >>> optimized = post_process_solution(solution, vehicle_config)
    >>> print(optimized["total_distance"])
"""

import copy
from typing import Any, Dict, List, Optional

from utils.geo import haversine_distance, route_distance_km
from logging_config import get_logger

logger = get_logger("green_vrp.route_optimize")


def two_opt_swap(
    stops: List[Dict[str, Any]], i: int, j: int
) -> List[Dict[str, Any]]:
    """
    执行一次 2-opt 交换。

    反转 stops[i:j] 之间的访问顺序（包含 i，不包含 j）。

    Args:
        stops: 路线站点列表（包含首尾的仓库）
        i: 第一个切点索引（不包含仓库起点 0）
        j: 第二个切点索引

    Returns:
        交换后的新路线站点列表

    Example:
        原始:  [仓库, A, B, C, D, 仓库]  (i=1, j=3)
        反转 A~C 段:  [仓库, C, B, A, D, 仓库]
    """
    if i >= j or i < 1 or j > len(stops) - 2:
        return stops

    new_stops = stops[:i] + stops[i:j + 1][::-1] + stops[j + 1:]
    return new_stops


def calculate_route_distance(stops: List[Dict[str, Any]]) -> float:
    """
    计算路线总里程（公里）。

    参数同 route_distance_km，此处为便捷封装。

    Args:
        stops: 站点列表

    Returns:
        总距离（公里）
    """
    return route_distance_km(stops)


def calculate_arrival_times(
    stops: List[Dict[str, Any]], speed_kmh: float
) -> List[Dict[str, Any]]:
    """
    给定车速，计算路线中各站点的到达时间。

    从仓库出发（arrival_time = 最早时间窗），
    依次累加行驶时间和服务时间得到下一站到达时间。

    Args:
        stops: 站点列表（需包含 lat, lon, service_time, tw_earliest）
        speed_kmh: 车速（公里/小时）

    Returns:
        填充了 arrival_time 和 departure_time 的站点列表副本
    """
    if not stops:
        return stops

    result = copy.deepcopy(stops)

    # 仓库出发时间 = 最早时间窗（如果没有则设为 0）
    current_time = result[0].get("tw_earliest", 480)
    if current_time is None:
        current_time = 480
    result[0]["arrival_time"] = current_time
    result[0]["departure_time"] = current_time

    for idx in range(1, len(result)):
        prev = result[idx - 1]
        curr = result[idx]

        # 计算从上一站到本站的行驶时间（分钟）
        dist_km = haversine_distance(
            prev["lat"], prev["lon"],
            curr["lat"], curr["lon"],
        )
        travel_time_min = (dist_km / speed_kmh) * 60

        # 到达时间 = 上一站离开时间 + 行驶时间
        prev_departure = prev.get("departure_time", prev.get("arrival_time", 0))
        arrival = prev_departure + travel_time_min

        # 如果早于最早时间窗，需要等待
        tw_earliest = curr.get("tw_earliest")
        if tw_earliest is not None and arrival < tw_earliest:
            arrival = int(tw_earliest)

        curr["arrival_time"] = int(arrival)

        # 离开时间 = 到达时间 + 服务时间
        service_time = curr.get("service_time", 0)
        curr["departure_time"] = int(arrival + service_time)

    return result


def check_time_window_feasibility(
    stops: List[Dict[str, Any]]
) -> bool:
    """
    检查路线中所有站点是否满足时间窗约束。

    Args:
        stops: 已计算 arrival_time 的站点列表

    Returns:
        是否全部满足时间窗
    """
    for stop in stops:
        node = stop.get("node", -1)
        if node == 0:
            continue  # 仓库不检查时间窗

        arrival = stop.get("arrival_time")
        tw_latest = stop.get("tw_latest")

        if arrival is not None and tw_latest is not None:
            if arrival > tw_latest + 30:  # 允许 30 分钟软迟到（与原求解器一致）
                return False
    return True


def optimize_single_route(
    stops: List[Dict[str, Any]],
    speed_kmh: float,
    capacity: float,
) -> Dict[str, Any]:
    """
    对单条路线执行 2-opt + Or-opt 局部优化。

    反复尝试 2-opt 交换和 Or-opt 平移（移动2~3个连续客户到新位置），
    接受能缩短距离且不违反时间窗的改进，直到无法进一步改进为止。

    Args:
        stops: 原始路线站点列表（含首尾仓库）
        speed_kmh: 车辆速度（公里/小时）
        capacity: 车辆容量（用于计算总需求量，不变）

    Returns:
        {
            "stops": 优化后的站点列表,
            "original_distance": 原始距离,
            "optimized_distance": 优化后距离,
            "improvement": 改进比例,
            "iterations": 交换次数,
        }
    """
    if not stops or len(stops) < 4:  # 至少需要 仓库-A-B-仓库 才能2-opt
        return {
            "stops": stops,
            "original_distance": calculate_route_distance(stops),
            "optimized_distance": calculate_route_distance(stops),
            "improvement": 0.0,
            "iterations": 0,
        }

    original_distance = calculate_route_distance(stops)
    best_stops = copy.deepcopy(stops)
    best_distance = original_distance
    iterations = 0
    improved = True

    n = len(best_stops)

    while improved:
        improved = False

        # === Phase 1: 2-opt 交换 ===
        for i in range(1, n - 2):
            for j in range(i + 2, n - 1):
                new_stops = two_opt_swap(best_stops, i, j)

                new_distance = calculate_route_distance(new_stops)
                if new_distance >= best_distance - 1e-6:
                    continue

                timed_stops = calculate_arrival_times(new_stops, speed_kmh)
                if not check_time_window_feasibility(timed_stops):
                    continue

                best_stops = new_stops
                best_distance = new_distance
                improved = True
                iterations += 1

        # === Phase 2: Or-opt 平移 (k=2,3) ===
        for k in (2, 3):
            for i in range(1, n - k):  # 子段起点
                for j in range(1, n):  # 目标位置
                    # 跳过子段自身范围
                    if i <= j < i + k:
                        continue

                    # Or-opt 平移：将 stops[i:i+k] 移动到 j 位置
                    segment = best_stops[i:i + k]
                    remaining = best_stops[:i] + best_stops[i + k:]
                    if j < i:
                        new_stops = remaining[:j] + segment + remaining[j:]
                    else:
                        # j >= i + k
                        new_stops = remaining[:j] + segment + remaining[j:]

                    new_distance = calculate_route_distance(new_stops)
                    if new_distance >= best_distance - 1e-6:
                        continue

                    timed_stops = calculate_arrival_times(new_stops, speed_kmh)
                    if not check_time_window_feasibility(timed_stops):
                        continue

                    best_stops = new_stops
                    best_distance = new_distance
                    improved = True
                    iterations += 1
                    n = len(best_stops)  # n 不变，路线长度变化不影响

    return {
        "stops": best_stops,
        "original_distance": original_distance,
        "optimized_distance": best_distance,
        "improvement": (
            (original_distance - best_distance) / original_distance * 100
            if original_distance > 0
            else 0.0
        ),
        "iterations": iterations,
    }


def _best_insert_position(
    stops: List[Dict[str, Any]],
    customer_stop: Dict[str, Any],
    speed_kmh: float,
) -> Tuple[int, float]:
    """
    在路线中找客户的最佳插入位置（使距离增量最小）。

    Args:
        stops: 现有路线（含首尾仓库）
        customer_stop: 要插入的客户站点
        speed_kmh: 车速

    Returns:
        (best_index, best_distance): 最佳插入索引和插入后的路线距离
    """
    best_idx = -1
    best_dist = float("inf")

    for i in range(1, len(stops)):
        new_stops = stops[:i] + [customer_stop] + stops[i:]
        # 检查时间窗
        timed = calculate_arrival_times(new_stops, speed_kmh)
        if not check_time_window_feasibility(timed):
            continue
        dist = calculate_route_distance(new_stops)
        if dist < best_dist:
            best_dist = dist
            best_idx = i

    return best_idx, best_dist


def relocate_between_routes(
    route_a: Dict[str, Any],
    route_b: Dict[str, Any],
    vehicle_config: Dict[str, Any],
) -> bool:
    """
    尝试将 route_a 中的每个客户搬迁到 route_b 中。

    如果搬迁后总距离下降且时间窗可行，则接受搬迁。

    Args:
        route_a: 源路线（从中取走客户）
        route_b: 目标路线（插入客户）
        vehicle_config: 车型配置

    Returns:
        是否发生了搬迁
    """
    speed_a = vehicle_config.get(route_a["vehicle_type"], {}).get("speed_kmh", 40)
    speed_b = vehicle_config.get(route_b["vehicle_type"], {}).get("speed_kmh", 40)
    capacity_b = route_b.get("capacity", 800)
    current_load_b = sum(
        s.get("demand", 0) for s in route_b["stops"] if s.get("node", -1) != 0
    )

    stops_a = route_a["stops"]
    stops_b = route_b["stops"]

    # 只尝试非仓库客户
    customer_indices = [
        i for i, s in enumerate(stops_a) if s.get("node", -1) != 0
    ]

    improved = False
    for idx in reversed(customer_indices):  # 从后往前避免索引漂移
        customer = stops_a[idx]
        demand = customer.get("demand", 0)

        # 容量检查
        if current_load_b + demand > capacity_b:
            continue

        # 找 route_b 中的最佳插入位置
        best_idx, new_dist_b = _best_insert_position(
            stops_b, customer, speed_b
        )
        if best_idx == -1:
            continue

        # 计算搬迁后的 route_a 距离
        new_stops_a = stops_a[:idx] + stops_a[idx + 1 :]
        timed_a = calculate_arrival_times(new_stops_a, speed_a)
        if not check_time_window_feasibility(timed_a):
            continue
        new_dist_a = calculate_route_distance(new_stops_a)

        # 判断是否改善（仅考虑距离节约，固定成本已由求解器处理）
        old_total = calculate_route_distance(stops_a) + calculate_route_distance(stops_b)
        new_total = new_dist_a + new_dist_b

        saving = old_total - new_total

        if saving > 1.0:  # 至少节省 1 km 才接受
            # 执行搬迁
            stops_b = stops_b[:best_idx] + [customer] + stops_b[best_idx:]
            stops_a = new_stops_a
            current_load_b += demand
            improved = True

    if improved:
        route_a["stops"] = stops_a
        route_b["stops"] = stops_b
        route_a["distance_km"] = round(calculate_route_distance(stops_a), 2)
        route_b["distance_km"] = round(calculate_route_distance(stops_b), 2)
        route_a["total_demand"] = sum(
            s.get("demand", 0) for s in stops_a if s.get("node", -1) != 0
        )
        route_b["total_demand"] = sum(
            s.get("demand", 0) for s in stops_b if s.get("node", -1) != 0
        )

    return improved


def exchange_between_routes(
    route_a: Dict[str, Any],
    route_b: Dict[str, Any],
    vehicle_config: Dict[str, Any],
) -> bool:
    """
    尝试交换 route_a 和 route_b 之间的客户。

    交换两个客户（各从对方路线取一个），
    如果总距离下降且都满足时间窗和容量约束则接受。

    Args:
        route_a: 路线A
        route_b: 路线B
        vehicle_config: 车型配置

    Returns:
        是否发生了交换
    """
    speed_a = vehicle_config.get(route_a["vehicle_type"], {}).get("speed_kmh", 40)
    speed_b = vehicle_config.get(route_b["vehicle_type"], {}).get("speed_kmh", 40)
    capacity_a = route_a.get("capacity", 800)
    capacity_b = route_b.get("capacity", 800)

    stops_a = route_a["stops"]
    stops_b = route_b["stops"]

    # 获取非仓库客户索引
    customers_a = [(i, s) for i, s in enumerate(stops_a) if s.get("node", -1) != 0]
    customers_b = [(i, s) for i, s in enumerate(stops_b) if s.get("node", -1) != 0]

    old_total = calculate_route_distance(stops_a) + calculate_route_distance(stops_b)

    best_swap = None
    best_new_total = old_total

    for i, cust_a in customers_a:
        for j, cust_b in customers_b:
            demand_a = cust_a.get("demand", 0)
            demand_b = cust_b.get("demand", 0)

            # 容量检查：交换后各自的负载
            load_a = sum(
                s.get("demand", 0) for s in stops_a if s.get("node", -1) != 0
            ) - demand_a + demand_b
            load_b = sum(
                s.get("demand", 0) for s in stops_b if s.get("node", -1) != 0
            ) - demand_b + demand_a

            if load_a > capacity_a or load_b > capacity_b:
                continue

            # 执行交换：route_a 的 cust_a -> route_b，route_b 的 cust_b -> route_a
            new_a = stops_a[:i] + stops_a[i + 1 :]
            # 在 new_a 中找到 cust_b 的最佳插入位置
            pos_a, dist_a = _best_insert_position(new_a, cust_b, speed_a)
            if pos_a == -1:
                continue

            new_b = stops_b[:j] + stops_b[j + 1 :]
            pos_b, dist_b = _best_insert_position(new_b, cust_a, speed_b)
            if pos_b == -1:
                continue

            new_total = dist_a + dist_b
            if new_total < best_new_total - 1.0:
                best_new_total = new_total
                best_swap = (i, j, new_a, new_b, pos_a, pos_b, cust_a, cust_b)

    if best_swap is not None:
        i, j, _, _, pos_a, pos_b, cust_a, cust_b = best_swap
        # 重建最终路线
        new_a = stops_a[:i] + stops_a[i + 1 :]
        new_a = new_a[:pos_a] + [cust_b] + new_a[pos_a:]
        new_b = stops_b[:j] + stops_b[j + 1 :]
        new_b = new_b[:pos_b] + [cust_a] + new_b[pos_b:]

        route_a["stops"] = new_a
        route_b["stops"] = new_b
        route_a["distance_km"] = round(calculate_route_distance(new_a), 2)
        route_b["distance_km"] = round(calculate_route_distance(new_b), 2)
        route_a["total_demand"] = sum(
            s.get("demand", 0) for s in new_a if s.get("node", -1) != 0
        )
        route_b["total_demand"] = sum(
            s.get("demand", 0) for s in new_b if s.get("node", -1) != 0
        )
        return True

    return False


def post_process_solution(
    solution: Dict[str, Any],
    vehicle_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    对求解结果进行 2-opt 后处理优化。

    遍历所有车辆的路线，对每路线执行 2-opt 优化，
    降低总距离并减少路径交叉。

    参数 solution 会被修改，同时返回修改后的引用。

    Args:
        solution: 求解结果字典（与 solver.solve() 返回值格式一致）
        vehicle_config: 车型配置字典

    Returns:
        优化后的求解结果字典

    Raises:
        ValueError: 如果路线中缺少必要字段（lat, lon）
    """
    optimized = copy.deepcopy(solution)

    if "routes" not in optimized or not optimized["routes"]:
        return optimized

    total_distance_saved = 0.0
    total_routes_improved = 0

    for route in optimized["routes"]:
        vehicle_type = route.get("vehicle_type", "4.2m")
        v_config = vehicle_config.get(vehicle_type, {})
        speed_kmh = v_config.get("speed_kmh", 40)
        capacity = v_config.get("capacity", 800)

        stops = route.get("stops", [])
        if not stops:
            continue

        # 验证必要字段
        for s in stops:
            if "lat" not in s or "lon" not in s:
                raise ValueError("路线站点缺少 lat/lon 字段")

        # 执行 2-opt 优化
        result = optimize_single_route(stops, speed_kmh, capacity)

        if result["iterations"] > 0:
            # 更新站点
            route["stops"] = result["stops"]
            route["distance_km"] = round(result["optimized_distance"], 2)
            total_distance_saved += result["original_distance"] - result["optimized_distance"]
            total_routes_improved += 1

            logger.info(
                "路线 %s(%s) 2-opt 优化: %.2f→%.2f km (节省 %.1f%%, %d次交换)",
                route.get("vehicle_type", "?"),
                route.get("vehicle_id", "?"),
                result["original_distance"],
                result["optimized_distance"],
                result["improvement"],
                result["iterations"],
            )

    # === 第二阶段：路线间 Relocate ===
    logger.info("开始路线间 Relocate 优化...")
    relocate_improved = _run_relocate_phase(optimized, vehicle_config)

    # === 第三阶段：路线间 Exchange ===
    if relocate_improved:
        logger.info("开始路线间 Exchange 优化...")
        _run_exchange_phase(optimized, vehicle_config)

    # 清理空路线（至少有一个客户站点）
    optimized["routes"] = [
        r for r in optimized["routes"]
        if any(s.get("node", -1) != 0 for s in r.get("stops", []))
    ]

    # 重新计算总距离
    total_km = sum(r.get("distance_km", 0.0) for r in optimized["routes"])
    optimized["total_distance"] = round(total_km, 2)
    optimized["vehicles_used"] = _count_vehicles_used(
        optimized["routes"], vehicle_config
    )

    return optimized


def _run_relocate_phase(
    solution: Dict[str, Any],
    vehicle_config: Dict[str, Any],
) -> bool:
    """执行多轮 Relocate 直到无法改进。"""
    overall_improved = False
    for _round in range(3):
        round_improved = False
        routes = solution["routes"]
        for i in range(len(routes)):
            for j in range(len(routes)):
                if i == j:
                    continue
                if relocate_between_routes(routes[i], routes[j], vehicle_config):
                    round_improved = True
                    overall_improved = True
        if not round_improved:
            break
    if overall_improved:
        logger.info("Relocate 优化完成")
    return overall_improved


def _run_exchange_phase(
    solution: Dict[str, Any],
    vehicle_config: Dict[str, Any],
) -> bool:
    """执行多轮 Exchange 直到无法改进。"""
    overall_improved = False
    for _round in range(3):
        round_improved = False
        routes = solution["routes"]
        for i in range(len(routes)):
            for j in range(i + 1, len(routes)):
                if exchange_between_routes(routes[i], routes[j], vehicle_config):
                    round_improved = True
                    overall_improved = True
        if not round_improved:
            break
    if overall_improved:
        logger.info("Exchange 优化完成")
    return overall_improved


def _count_vehicles_used(
    routes: List[Dict[str, Any]],
    vehicle_config: Dict[str, Any],
) -> Dict[str, int]:
    """统计各车型实际使用的车辆数。"""
    used = {v_type: 0 for v_type in vehicle_config}
    for r in routes:
        v_type = r.get("vehicle_type", "4.2m")
        if v_type in used:
            used[v_type] += 1
    return used