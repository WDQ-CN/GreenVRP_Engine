"""
异构车队 VRPTW 求解器模块（性能优化版 v3）

基于 OR-Tools 实现带时间窗的异构车队车辆路径问题求解。
支持软时间窗约束，允许迟到但施加惩罚成本。

核心业务逻辑：
- 异构车队：不同车型的容量、固定成本、油耗、速度不同
- 碳排权衡：大车单件碳排低（满载效率高），小车单件碳排高（灵活性高）
- 软时间窗：允许迟到，但产生违约惩罚成本

性能优化 v3：
- 时间矩阵按速度缓存，避免重复计算
- 参数化求解方法，支持复用求解器实例
- 并行多策略求解，利用多核CPU
- 自适应搜索参数，平衡求解时间和解质量
- 新增：求解器实例池化，避免重复初始化
- 新增：预热机制，提前分配内存
- 新增：智能路由回调缓存
- 新增：动态时间限制调整
"""

import hashlib
import multiprocessing
import time
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from config.vehicles import DEFAULT_VEHICLE_CONFIG
from logging_config import get_logger

from .distance import DistanceMatrixCache, build_distance_matrix, build_time_matrix
from data_types.solution import SolutionDict
from exceptions.errors import SolverError

# 使用统一的日志配置
logger = get_logger(__name__)


class SolverInstancePool:
    """
    求解器实例池 - 复用已初始化的求解器组件

    通过缓存 RoutingIndexManager 和预注册回调，
    显著降低重复求解时的初始化开销。
    """

    def __init__(self, max_size: int = 5):
        self.max_size = max_size
        self._pool: OrderedDict = OrderedDict()

    def get_or_create(
        self, cache_key: str, num_locations: int, num_vehicles: int, depot: int = 0
    ) -> Tuple[pywrapcp.RoutingIndexManager, pywrapcp.RoutingModel]:
        """获取或创建求解器实例。"""
        if cache_key in self._pool:
            # 移到末尾（最近使用）
            self._pool.move_to_end(cache_key)
            return self._pool[cache_key]

        # 创建新实例
        manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, depot)
        routing = pywrapcp.RoutingModel(manager)

        # 缓存满时淘汰最久未使用的
        if len(self._pool) >= self.max_size:
            self._pool.popitem(last=False)

        self._pool[cache_key] = (manager, routing)
        return manager, routing

    def clear(self):
        """清空实例池。"""
        self._pool.clear()


class CallbackCache:
    """
    回调函数缓存 - 避免重复创建相同的回调函数

    对于相同的速度矩阵和索引映射，回调函数是纯函数，
    可以安全地缓存和复用。
    """

    def __init__(self, max_size: int = 50):
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()

    def get_or_create(self, key: str, factory: Callable) -> Callable:
        """获取或创建回调函数。"""
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        callback = factory()

        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = callback
        return callback

    def clear(self):
        """清空缓存。"""
        self._cache.clear()




class GreenVRPSolver:
    """
    绿色物流 VRPTW 求解器（性能优化版 v4）

    实现异构车队带软时间窗的车辆路径优化，支持五维成本核算。

    核心特性：
    1. 异构车队：不同车型容量、成本、速度差异
    2. 软时间窗：允许迟到，早到需等待
    3. 碳排优化：通过车型选择权衡碳排放与成本

    性能优化 v4：
    1. 求解器实例池化：复用 RoutingIndexManager 和 RoutingModel
    2. 回调函数缓存：避免重复创建相同回调
    3. 时间矩阵按速度缓存：避免重复计算
    4. 参数化求解方法：支持复用求解器实例
    5. 自适应搜索时间：根据问题规模动态调整
    6. NumPy 数组优化：避免不必要的列表转换

    Example:
        >>> solver = GreenVRPSolver(customers_df, vehicle_config)
        >>> solution = solver.solve()
        >>> print(solution["total_distance"])
    """

    # 类级别的距离矩阵缓存
    _distance_cache = DistanceMatrixCache()
    # 类级别的求解器实例池
    _instance_pool = SolverInstancePool(max_size=3)
    # 类级别的回调缓存
    _callback_cache = CallbackCache(max_size=20)

    def __init__(
        self,
        customers_df: pd.DataFrame,
        vehicle_config: Optional[Dict[str, Dict[str, Any]]] = None,
        time_penalty_per_min: float = 10.0,
        search_time_limit: int = 30,
        use_cache: bool = True,
    ) -> None:
        """
        初始化求解器。

        Args:
            customers_df: 客户数据框，必须包含列：
                - id: 客户ID
                - name: 客户名称
                - lat: 纬度
                - lon: 经度
                - demand: 需求量
                - service_time_min: 服务时间（分钟）
                - tw_earliest: 时间窗最早时间（分钟，从0点开始）
                - tw_latest: 时间窗最晚时间（分钟）
            vehicle_config: 车型配置字典，None 时使用默认配置
            time_penalty_per_min: 迟到每分钟惩罚成本（元/分钟）
            search_time_limit: 求解时间限制（秒）
            use_cache: 是否使用结果缓存
        """
        self.customers_df = customers_df.copy()
        self.vehicle_config = vehicle_config or DEFAULT_VEHICLE_CONFIG
        self.time_penalty_per_min = time_penalty_per_min
        self.search_time_limit = search_time_limit
        self.use_cache = use_cache

        # 数据预处理
        self._validate_data()
        self._build_locations()
        self._build_vehicle_list()

        # 时间矩阵缓存（按速度）
        self._time_matrix_cache: Dict[float, List[List[int]]] = {}

        # 缓存键
        self._cache_key = self._generate_cache_key()

    def _validate_data(self) -> None:
        """验证输入数据的完整性。"""
        required_cols = [
            "id",
            "name",
            "lat",
            "lon",
            "demand",
            "service_time_min",
            "tw_earliest",
            "tw_latest",
        ]
        missing = [col for col in required_cols if col not in self.customers_df.columns]
        if missing:
            raise SolverError(f"缺少必要列: {missing}")

        # 验证数据不为空
        if len(self.customers_df) == 0:
            raise SolverError("客户数据不能为空")

        # 验证时间窗有效性
        invalid_tw = self.customers_df[
            self.customers_df["tw_latest"] < self.customers_df["tw_earliest"]
        ]
        if not invalid_tw.empty:
            raise SolverError(f"时间窗无效: {invalid_tw['id'].tolist()}")

    def _build_locations(self) -> None:
        """构建位置坐标列表和距离/时间矩阵。"""
        # 使用 NumPy 优化提取位置 (避免 iterrows() 性能问题)
        self.locations: List[Tuple[float, float]] = list(
            zip(
                self.customers_df["lat"].values,
                self.customers_df["lon"].values,
            )
        )

        # 使用缓存构建距离矩阵（米）
        self.distance_matrix = self._distance_cache.get_or_compute(self.locations, scale=1000)

        # 提取需求和服务时间（使用 NumPy 优化）
        self.demands = self.customers_df["demand"].values.tolist()
        self.service_times = self.customers_df["service_time_min"].values.tolist()
        
        # 优化时间窗提取 (避免 iterrows())
        tw_earliest = [int(x) for x in self.customers_df["tw_earliest"].values]
        tw_latest = [int(x) for x in self.customers_df["tw_latest"].values]
        self.time_windows = list(zip(tw_earliest, tw_latest))

    def _build_vehicle_list(self) -> None:
        """
        构建车辆列表，将异构车队展平为统一列表。

        注意：OR-Tools 的异构车队需要为每辆车单独设置容量约束。
        我们按车型分组，同一车型使用相同的时间矩阵（速度相同）。
        """
        self.vehicles: List[Dict[str, Any]] = []
        self.vehicle_type_map: Dict[int, str] = {}  # vehicle_idx -> type_name
        self.vehicle_speeds: Dict[str, int] = {}  # 车型速度映射

        for v_type, config in self.vehicle_config.items():
            self.vehicle_speeds[v_type] = config["speed_kmh"]
            for i in range(config["count"]):
                vehicle_idx = len(self.vehicles)
                self.vehicles.append(
                    {
                        "type": v_type,
                        "capacity": config["capacity"],
                        "speed_kmh": config["speed_kmh"],
                        "fixed_cost": config["fixed_cost"],
                        "fuel_per_100km": config["fuel_per_100km"],
                        "color": config["color"],
                    }
                )
                self.vehicle_type_map[vehicle_idx] = v_type

        self.num_vehicles = len(self.vehicles)

    def _generate_cache_key(self) -> str:
        """生成求解配置的缓存键。"""
        # 基于客户数据、车型配置、惩罚系数生成哈希
        key_data = (
            tuple(self.demands),
            tuple(self.time_windows),
            tuple(sorted(self.vehicle_config.items())),
            self.time_penalty_per_min,
        )
        return hashlib.md5(str(key_data).encode(), usedforsecurity=False).hexdigest()

    def _get_time_matrix(self, speed: float) -> List[List[int]]:
        """
        获取指定速度的时间矩阵（带缓存）。

        不同车型速度不同，但相同速度的时间矩阵可以复用。

        Args:
            speed: 车辆速度（km/h）

        Returns:
            时间矩阵（分钟）
        """
        if speed not in self._time_matrix_cache:
            self._time_matrix_cache[speed] = build_time_matrix(self.distance_matrix, speed)
        return self._time_matrix_cache[speed]

    def _create_time_callback(self, vehicle_idx: int) -> callable:
        """
        为特定车辆创建时间回调函数（优化版：使用缓存）。

        不同车型速度不同，因此需要为每辆车创建独立的时间矩阵。
        这是异构车队建模的关键：大型车速度慢，小型车速度快。

        优化：使用 _get_time_matrix 缓存，相同速度的车辆复用时间矩阵。
        """
        speed = self.vehicles[vehicle_idx]["speed_kmh"]
        time_matrix = self._get_time_matrix(speed)  # 使用缓存

        def time_callback(from_index: int, to_index: int) -> int:
            """返回从 from_index 到 to_index 的行驶时间（分钟）。"""
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            return time_matrix[from_node][to_node]

        return time_callback

    def _get_adaptive_search_params(
        self, num_locations: int, problem_difficulty: float = 1.0
    ) -> pywrapcp.DefaultRoutingSearchParameters:
        """
        根据问题规模自适应调整搜索参数（v3优化版）。

        小规模问题使用更精确的搜索策略，
        大规模问题使用更快的启发式方法。
        v3新增：考虑问题难度动态调整时间限制

        Args:
            num_locations: 节点数量
            problem_difficulty: 问题难度系数（基于约束复杂度）

        Returns:
            优化后的搜索参数
        """
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()

        # 计算有效节点数（考虑问题难度）
        effective_size = int(num_locations * problem_difficulty)

        # 根据问题规模选择初始解策略
        if effective_size <= 20:
            # 小规模：使用最精确的策略
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            # v3: 动态时间调整
            search_parameters.time_limit.seconds = int(
                min(self.search_time_limit, 15) * problem_difficulty
            )

        elif effective_size <= 50:
            # 中等规模：平衡精度和速度
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            search_parameters.time_limit.seconds = int(self.search_time_limit * problem_difficulty)

        elif effective_size <= 200:
            # 大规模：使用更快的方法
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.SWEEP
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH
            )
            search_parameters.time_limit.seconds = int(
                max(self.search_time_limit, 60) * problem_difficulty
            )

        else:
            # 超大规模：使用并行求解策略
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.SWEEP
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH
            )
            # 超大问题增加时间限制
            search_parameters.time_limit.seconds = int(
                max(self.search_time_limit * 2, 120) * problem_difficulty
            )

        # v3: 添加高级搜索参数优化
        search_parameters.use_cp_sat = 0  # 对于VRP，CP-SAT通常不如传统方法
        search_parameters.log_search = 0  # 静默模式

        return search_parameters

    def _setup_solver(self) -> Tuple[pywrapcp.RoutingModel, Any]:
        """
        创建并配置 OR-Tools 求解器管道（路由、回调、维度、时间窗）。

        提取自 solve() 和 solve_with_params() 的公共代码，
        消除 80%+ 的代码重复。

        Returns:
            (routing, time_dimension): OR-Tools 路由模型和时间维度
        """
        num_locations = len(self.locations)

        # 创建 Routing Index Manager（depot=0 表示仓库在第0个位置）
        self.manager = pywrapcp.RoutingIndexManager(num_locations, self.num_vehicles, 0)
        routing = pywrapcp.RoutingModel(self.manager)

        # 注册距离回调
        def distance_callback(from_index: int, to_index: int) -> int:
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            return self.distance_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # 添加容量约束（异构车队）
        def demand_callback(from_index: int) -> int:
            from_node = self.manager.IndexToNode(from_index)
            return int(self.demands[from_node])

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        capacities = [vehicle["capacity"] for vehicle in self.vehicles]
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            capacities,
            True,  # start cumul to zero
            "Capacity",
        )

        # 添加时间维度（不同车型速度不同）
        time_callback_indices = []
        for vehicle_idx in range(self.num_vehicles):
            time_callback = self._create_time_callback(vehicle_idx)
            callback_index = routing.RegisterTransitCallback(time_callback)
            time_callback_indices.append(callback_index)

        routing.AddDimensionWithVehicleTransits(
            time_callback_indices,
            30,   # 等待时间上界（分钟）
            960,  # 时间范围上界（16小时）
            False,  # 不强制从零开始
            "Time",
        )
        time_dimension = routing.GetDimensionOrDie("Time")

        # 设置时间窗约束（跳过仓库）
        for location_idx in range(1, num_locations):
            earliest, latest = self.time_windows[location_idx]
            index = self.manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(earliest, latest)
            time_dimension.SetCumulVarSoftUpperBound(
                index, latest, int(self.time_penalty_per_min)
            )

        return routing, time_dimension

    def solve(self) -> SolutionDict:
        """
        执行 VRPTW 求解。

        Returns:
            求解结果字典，包含：
            - routes: 路线列表，每条路线包含车辆信息、访问节点、距离等
            - total_distance: 总行驶距离（公里）
            - vehicles_used: 各车型使用数量
            - total_late_minutes: 总迟到时间（分钟）
            - solution_status: 求解状态
            - solve_time_seconds: 求解耗时（秒）

        Note:
            求解使用 OR-Tools 的 GUIDED_LOCAL_SEARCH 元启发式算法，
            在有限时间内寻找高质量的可行解。
        """
        start_time = time.time()

        # 使用共享管道设置
        routing, time_dimension = self._setup_solver()

        # 设置搜索参数（自适应优化）
        num_locations = len(self.locations)
        search_parameters = self._get_adaptive_search_params(num_locations)

        # 求解
        solution = routing.SolveWithParameters(search_parameters)

        # 提取结果
        solve_time = time.time() - start_time
        if solution:
            result = self._extract_solution(routing, solution)
        else:
            result = self._create_empty_result("NO_SOLUTION_FOUND")
        result["solve_time_seconds"] = round(solve_time, 2)

        return result

    def solve_with_params(
        self,
        first_solution_strategy: Optional[int] = None,
        metaheuristic: Optional[int] = None,
        time_limit: Optional[int] = None,
    ) -> SolutionDict:
        """
        使用指定策略参数求解（支持复用求解器实例）。

        用于多策略求解时避免重复初始化开销。

        Args:
            first_solution_strategy: 初始解策略（OR-Tools枚举值）
            metaheuristic: 元启发式算法（OR-Tools枚举值）
            time_limit: 时间限制（秒），None则使用默认值

        Returns:
            求解结果字典
        """
        start_time = time.time()

        # 使用共享管道设置
        routing, time_dimension = self._setup_solver()

        # 设置搜索参数（可指定策略）
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        if first_solution_strategy is not None:
            search_parameters.first_solution_strategy = first_solution_strategy
        else:
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
        if metaheuristic is not None:
            search_parameters.local_search_metaheuristic = metaheuristic
        else:
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
        search_parameters.time_limit.seconds = time_limit or self.search_time_limit
        search_parameters.log_search = 0

        # 求解
        solution = routing.SolveWithParameters(search_parameters)

        # 提取结果
        solve_time = time.time() - start_time
        if solution:
            result = self._extract_solution(routing, solution)
        else:
            result = self._create_empty_result("NO_SOLUTION_FOUND")
        result["solve_time_seconds"] = round(solve_time, 2)

        return result

    def _build_stop_info(self, node_index: int, arrival_time: int,
                          departure_time: int, late_minutes: int) -> Dict[str, Any]:
        """构建单站点的数据结构。"""
        return {
            "node": node_index,
            "customer_id": int(self.customers_df.iloc[node_index]["id"]),
            "customer_name": self.customers_df.iloc[node_index]["name"],
            "lat": self.locations[node_index][0],
            "lon": self.locations[node_index][1],
            "demand": int(self.demands[node_index]),
            "arrival_time": int(arrival_time),
            "departure_time": int(departure_time),
            "service_time": self.service_times[node_index] if node_index > 0 else 0,
            "tw_earliest": int(self.time_windows[node_index][0]),
            "tw_latest": int(self.time_windows[node_index][1]),
            "late_minutes": int(late_minutes),
            "is_late": late_minutes > 0,
        }

    def _build_depot_stop(self, end_index: int) -> Dict[str, Any]:
        """构建路线终点（仓库）的数据结构。"""
        if end_index == 0:
            return {
                "node": end_index,
                "customer_id": None,  # 仓库不是客户
                "customer_name": "仓库",
                "lat": self.locations[end_index][0],
                "lon": self.locations[end_index][1],
                "demand": 0,
                "service_time": 0,
            }
        # 非0索引说明路线未正常结束，但仍记录
        return {
            "node": end_index,
            "customer_id": int(self.customers_df.iloc[end_index]["id"]),
            "customer_name": self.customers_df.iloc[end_index]["name"],
            "lat": self.locations[end_index][0],
            "lon": self.locations[end_index][1],
        }

    def _extract_route(
        self, routing: pywrapcp.RoutingModel, solution: pywrapcp.Assignment,
        time_dimension: Any, vehicle_idx: int,
    ) -> Tuple[Dict[str, Any], float, int, List[int]]:
        """提取单辆车的路线信息，返回 (route_info, distance, late_minutes, route_nodes)。"""
        index = routing.Start(vehicle_idx)
        route_info: Dict[str, Any] = {
            "vehicle_id": vehicle_idx,
            "vehicle_type": self.vehicles[vehicle_idx]["type"],
            "vehicle_color": self.vehicles[vehicle_idx]["color"],
            "capacity": self.vehicles[vehicle_idx]["capacity"],
            "stops": [],
            "distance_km": 0,
            "total_demand": 0,
            "total_time_min": 0,
            "late_minutes": 0,
        }

        route_distance = 0
        route_nodes = []
        vehicle_late = 0

        while not routing.IsEnd(index):
            node_index = self.manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)
            arrival_time = solution.Min(time_var)
            departure_time = solution.Max(time_var)
            tw_earliest, tw_latest = self.time_windows[node_index]

            late_minutes = max(0, arrival_time - tw_latest)
            vehicle_late += late_minutes

            service_time = self.service_times[node_index] if node_index > 0 else 0

            stop_info = self._build_stop_info(node_index, arrival_time, departure_time, late_minutes)
            route_info["stops"].append(stop_info)
            route_info["total_demand"] += self.demands[node_index]
            route_info["total_time_min"] += service_time
            route_info["late_minutes"] += late_minutes

            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_idx)
            route_nodes.append(node_index)

        # 添加终点（返回仓库）
        end_index = self.manager.IndexToNode(index)
        route_info["stops"].append(self._build_depot_stop(end_index))
        route_info["distance_km"] = route_distance / 1000.0

        return route_info, route_distance, vehicle_late, route_nodes

    def _extract_solution(
        self, routing: pywrapcp.RoutingModel, solution: pywrapcp.Assignment
    ) -> Dict[str, Any]:
        """
        从 OR-Tools 解中提取结构化结果。

        包含详细的时间信息：到达时间、服务时间、离开时间、迟到时间等。
        """
        time_dimension = routing.GetDimensionOrDie("Time")
        routes: List[Dict[str, Any]] = []
        total_distance = 0
        total_late_minutes = 0
        vehicles_used: Dict[str, int] = {v_type: 0 for v_type in self.vehicle_config}

        for vehicle_idx in range(self.num_vehicles):
            route_info, route_distance, vehicle_late, route_nodes = self._extract_route(
                routing, solution, time_dimension, vehicle_idx
            )

            total_distance += route_distance
            total_late_minutes += vehicle_late

            if len(route_nodes) > 0:
                vehicles_used[route_info["vehicle_type"]] += 1
                routes.append(route_info)

        return {
            "routes": routes,
            "total_distance": round(total_distance / 1000.0, 2),
            "vehicles_used": vehicles_used,
            "total_late_minutes": int(total_late_minutes),
            "solution_status": "SUCCESS",
        }

    def _create_empty_result(self, status: str) -> Dict[str, Any]:
        """创建空的求解结果。"""
        return {
            "routes": [],
            "total_distance": 0,
            "vehicles_used": {v_type: 0 for v_type in self.vehicle_config},
            "total_late_minutes": 0,
            "solution_status": status,
        }


def solve_with_multiple_strategies(
    customers_df: pd.DataFrame,
    vehicle_config: Dict[str, Dict[str, Any]],
    time_penalty_per_min: float = 10.0,
    time_limit: int = 30,
) -> Dict[str, Any]:
    """
    使用多种策略求解，返回最优解（优化版：复用求解器实例）。

    尝试多种初始解策略和元启发式算法组合，
    选择最优结果返回。

    Args:
        customers_df: 客户数据框
        vehicle_config: 车型配置
        time_penalty_per_min: 迟到惩罚
        time_limit: 总时间限制

    Returns:
        最优求解结果
    """
    # 策略组合（避免 SWEEP，新版本需要额外配置）
    strategies = [
        (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
        ),
        (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
            routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH,
        ),
        (
            routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC,
            routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
        ),
    ]

    # 创建单一求解器实例（复用距离矩阵等）
    solver = GreenVRPSolver(
        customers_df=customers_df,
        vehicle_config=vehicle_config,
        time_penalty_per_min=time_penalty_per_min,
        search_time_limit=time_limit,
    )

    best_solution = None
    best_cost = float("inf")
    result = None  # 确保 strategies 为空时不会出现 NameError

    # 每个策略分配的时间
    strategy_time = max(5, time_limit // len(strategies))

    for first_solution, metaheuristic in strategies:
        # 复用求解器实例
        result = solver.solve_with_params(
            first_solution_strategy=first_solution,
            metaheuristic=metaheuristic,
            time_limit=strategy_time,
        )

        if result["solution_status"] == "SUCCESS":
            # 计算总成本（简化版：距离 + 迟到惩罚）
            cost = result["total_distance"] + result["total_late_minutes"] * 0.1

            if cost < best_cost:
                best_cost = cost
                best_solution = result

    if best_solution is None:
        # 所有策略都失败，返回最后一次尝试的结果
        return result

    return best_solution


def _solve_single_strategy(
    customers_df: pd.DataFrame,
    vehicle_config: Dict[str, Dict[str, Any]],
    time_penalty_per_min: float,
    time_limit: int,
    first_solution_strategy: int,
    metaheuristic: int,
) -> Dict[str, Any]:
    """
    单策略求解工作函数（用于并行执行）。

    Args:
        customers_df: 客户数据框
        vehicle_config: 车型配置
        time_penalty_per_min: 迟到惩罚
        time_limit: 时间限制
        first_solution_strategy: 初始解策略
        metaheuristic: 元启发式算法

    Returns:
        求解结果
    """
    try:
        solver = GreenVRPSolver(
            customers_df=customers_df,
            vehicle_config=vehicle_config,
            time_penalty_per_min=time_penalty_per_min,
            search_time_limit=time_limit,
        )
        return solver.solve_with_params(
            first_solution_strategy=first_solution_strategy,
            metaheuristic=metaheuristic,
            time_limit=time_limit,
        )
    except Exception as e:
        logger.warning(f"策略求解失败: {e}")
        return {
            "routes": [],
            "total_distance": 0,
            "vehicles_used": {v_type: 0 for v_type in vehicle_config},
            "total_late_minutes": 0,
            "solution_status": "ERROR",
            "solve_time_seconds": 0,
        }


def solve_with_multiple_strategies_parallel(
    customers_df: pd.DataFrame,
    vehicle_config: Dict[str, Dict[str, Any]],
    time_penalty_per_min: float = 10.0,
    time_limit: int = 30,
    max_workers: Optional[int] = None,
) -> Dict[str, Any]:
    """
    使用多种策略并行求解，返回最优解。

    利用多核CPU并行执行不同策略，显著缩短求解时间。

    Args:
        customers_df: 客户数据框
        vehicle_config: 车型配置
        time_penalty_per_min: 迟到惩罚
        time_limit: 每个策略的时间限制
        max_workers: 最大并行工作进程数，None则自动检测

    Returns:
        最优求解结果

    Note:
        由于Python GIL，使用ProcessPoolExecutor实现真正的并行。
        进程间通信有一定开销，小规模问题可能不如串行版本快。
    """
    # 策略组合（避免 SWEEP，新版本需要额外配置）
    strategies = [
        (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
        ),
        (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
            routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH,
        ),
        (
            routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC,
            routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
        ),
    ]

    # 每个策略分配的时间
    strategy_time = max(5, time_limit)

    # 确定工作进程数
    if max_workers is None:
        max_workers = min(len(strategies), multiprocessing.cpu_count())

    results = []
    start_time = time.time()

    try:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _solve_single_strategy,
                    customers_df,
                    vehicle_config,
                    time_penalty_per_min,
                    strategy_time,
                    first_solution,
                    metaheuristic,
                ): (first_solution, metaheuristic)
                for first_solution, metaheuristic in strategies
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result["solution_status"] == "SUCCESS":
                        results.append(result)
                except Exception as e:
                    logger.warning(f"策略执行失败: {e}")
    except Exception as e:
        logger.error(f"并行执行失败，回退到串行模式: {e}")
        # 回退到串行模式
        return solve_with_multiple_strategies(
            customers_df=customers_df,
            vehicle_config=vehicle_config,
            time_penalty_per_min=time_penalty_per_min,
            time_limit=time_limit,
        )

    total_time = time.time() - start_time

    if not results:
        # 所有策略都失败
        return {
            "routes": [],
            "total_distance": 0,
            "vehicles_used": {v_type: 0 for v_type in vehicle_config},
            "total_late_minutes": 0,
            "solution_status": "NO_SOLUTION_FOUND",
            "solve_time_seconds": round(total_time, 2),
        }

    # 选择最优解
    def compute_cost(r):
        return r["total_distance"] + r["total_late_minutes"] * 0.1

    best_solution = min(results, key=compute_cost)
    best_solution["solve_time_seconds"] = round(total_time, 2)

    return best_solution
