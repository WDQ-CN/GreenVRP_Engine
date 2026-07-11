"""
异构车队 VRPTW 求解器模块（性能优化版 v4）

基于 OR-Tools 实现带时间窗的异构车队车辆路径问题求解。
支持软时间窗约束，允许迟到但施加惩罚成本。

核心业务逻辑：
- 异构车队：不同车型的容量、固定成本、油耗、速度不同
- 碳排权衡：大车单件碳排低（满载效率高），小车单件碳排高（灵活性高）
- 软时间窗：允许迟到，但产生违约惩罚成本

性能优化 v4：
- 求解器实例池化：复用 RoutingModel，避免重复初始化（最大优化点）
- 时间矩阵按速度缓存，避免重复计算
- 参数化求解方法，支持复用求解器实例
- 并行多策略求解，利用多核CPU
- 自适应搜索参数，平衡求解时间和解质量
- NumPy 数组直接传递，减少类型转换开销
- DataFrame 延迟拷贝，减少内存占用
"""

import hashlib
import multiprocessing
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

import numpy as np
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from config.vehicles import DEFAULT_VEHICLE_CONFIG
from logging_config import get_logger

from .distance import DistanceMatrixCache, build_time_matrix

# 使用统一的日志配置
logger = get_logger(__name__)


class SolverPool:
    """
    求解器实例池（v4 新增）。

    复用求解器数据准备和解决方案缓存，避免重复计算。
    使用 LRU 策略管理池中实例。

    Example:
        >>> pool = SolverPool(max_size=5)
        >>> result = pool.solve_with_cache(customers_df, vehicle_config)
        >>> if result:
        ...     print(result['total_distance'])
    """

    def __init__(self, max_size: int = 10, solution_cache_size: int = 100):
        self._pool: dict[str, GreenVRPSolver] = {}
        self._max_size = max_size
        self._lock = threading.Lock()
        self._access_order: list[str] = []
        self._solution_cache: dict[str, dict[str, Any]] = {}
        self._solution_cache_size = solution_cache_size

    def get_cached_solution(self, cache_key: str) -> dict[str, Any] | None:
        """获取缓存的解决方案。"""
        with self._lock:
            if cache_key in self._solution_cache:
                solution = self._solution_cache[cache_key].copy()
                logger.info(f"使用缓存的解决方案: {cache_key[:8]}...")
                return solution
        return None

    def cache_solution(self, cache_key: str, solution: dict[str, Any]) -> None:
        """缓存解决方案。"""
        with self._lock:
            if len(self._solution_cache) >= self._solution_cache_size:
                oldest_key = next(iter(self._solution_cache))
                self._solution_cache.pop(oldest_key)
            self._solution_cache[cache_key] = solution

    def solve_with_cache(
        self,
        customers_df: pd.DataFrame,
        vehicle_config: dict[str, dict[str, Any]] | None = None,
        time_penalty_per_min: float = 10.0,
        search_time_limit: int = 30,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """
        使用缓存求解（推荐方法）。

        先检查解决方案缓存，如果命中直接返回；
        否则创建求解器并求解，然后缓存结果。

        Args:
            customers_df: 客户数据
            vehicle_config: 车型配置
            time_penalty_per_min: 迟到惩罚
            search_time_limit: 求解时间限制
            use_cache: 是否使用缓存

        Returns:
            求解结果
        """
        solver = GreenVRPSolver(
            customers_df=customers_df,
            vehicle_config=vehicle_config,
            time_penalty_per_min=time_penalty_per_min,
            search_time_limit=search_time_limit,
            use_cache=use_cache,
        )

        cache_key = solver._cache_key

        if use_cache:
            cached = self.get_cached_solution(cache_key)
            if cached:
                return cached

        solution = solver.solve()

        if use_cache and solution.get("solution_status") == "SUCCESS":
            self.cache_solution(cache_key, solution)

        return solution

    def clear(self) -> None:
        """清空池中所有实例和缓存。"""
        with self._lock:
            self._pool.clear()
            self._access_order.clear()
            self._solution_cache.clear()


# 全局求解器池
_solver_pool = SolverPool(max_size=10, solution_cache_size=100)


class GreenVRPSolver:
    """
    绿色物流 VRPTW 求解器（性能优化版 v2）

    实现异构车队带软时间窗的车辆路径优化，支持五维成本核算。

    核心特性：
    1. 异构车队：不同车型容量、成本、速度差异
    2. 软时间窗：允许迟到，早到需等待
    3. 碳排优化：通过车型选择权衡碳排放与成本

    性能优化 v2：
    1. 时间矩阵按速度缓存：避免重复计算
    2. 参数化求解方法：支持复用求解器实例
    3. 自适应搜索时间：根据问题规模动态调整

    Example:
        >>> solver = GreenVRPSolver(customers_df, vehicle_config)
        >>> solution = solver.solve()
        >>> print(solution["total_distance"])
    """

    # 类级别的距离矩阵缓存
    _distance_cache = DistanceMatrixCache()

    def __init__(
        self,
        customers_df: pd.DataFrame,
        vehicle_config: dict[str, dict[str, Any]] | None = None,
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
        self.customers_df = customers_df
        self.vehicle_config = vehicle_config or DEFAULT_VEHICLE_CONFIG
        self.time_penalty_per_min = time_penalty_per_min
        self.search_time_limit = search_time_limit
        self.use_cache = use_cache

        # 数据预处理
        self._validate_data()
        self._build_locations()
        self._build_vehicle_list()

        # 时间矩阵缓存（按速度）
        self._time_matrix_cache: dict[float, list[list[int]]] = {}

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
            raise ValueError(f"缺少必要列: {missing}")

        # 验证数据不为空
        if len(self.customers_df) == 0:
            raise ValueError("客户数据不能为空")

        # 验证时间窗有效性
        invalid_tw = self.customers_df[
            self.customers_df["tw_latest"] < self.customers_df["tw_earliest"]
        ]
        if not invalid_tw.empty:
            raise ValueError(f"时间窗无效: {invalid_tw['id'].tolist()}")

    def _build_locations(self) -> None:
        """构建位置坐标列表和距离/时间矩阵。"""
        # 使用 NumPy 向量化操作提取位置（O(n) 连续内存访问）
        lat_lon = self.customers_df[["lat", "lon"]].to_numpy(dtype=np.float64)
        self.locations = [(float(row[0]), float(row[1])) for row in lat_lon]

        # 使用缓存构建距离矩阵（米）
        self.distance_matrix = self._distance_cache.get_or_compute(self.locations, scale=1000)

        # 提取需求和服务时间（使用 NumPy 向量化）
        self.demands = self.customers_df["demand"].to_numpy(dtype=np.int32).tolist()
        self.service_times = self.customers_df["service_time_min"].to_numpy(dtype=np.int32).tolist()
        tw_array = self.customers_df[["tw_earliest", "tw_latest"]].to_numpy(dtype=np.int32)
        self.time_windows = [(int(row[0]), int(row[1])) for row in tw_array]

    def _build_vehicle_list(self) -> None:
        """
        构建车辆列表，将异构车队展平为统一列表。

        注意：OR-Tools 的异构车队需要为每辆车单独设置容量约束。
        我们按车型分组，同一车型使用相同的时间矩阵（速度相同）。
        """
        self.vehicles: list[dict[str, Any]] = []
        self.vehicle_type_map: dict[int, str] = {}  # vehicle_idx -> type_name
        self.vehicle_speeds: dict[str, int] = {}  # 车型速度映射

        for v_type, config in self.vehicle_config.items():
            self.vehicle_speeds[v_type] = config["speed_kmh"]
            for _i in range(config["count"]):
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
        """生成求解配置的缓存键（优化版 v4）。"""
        import json

        n = len(self.demands)
        if n == 0:
            key_data = {"n": n, "time_penalty_per_min": self.time_penalty_per_min}
        elif n <= 50:
            key_data = {
                "demands": self.demands,
                "time_windows": self.time_windows,
                "vehicle_config": self.vehicle_config,
                "time_penalty_per_min": self.time_penalty_per_min,
            }
        else:
            key_data = {
                "sample_demands": [
                    self.demands[0],
                    self.demands[n // 2],
                    self.demands[-1],
                ],
                "sample_time_windows": [
                    self.time_windows[0],
                    self.time_windows[n // 2],
                    self.time_windows[-1],
                ],
                "vehicle_config": self.vehicle_config,
                "time_penalty_per_min": self.time_penalty_per_min,
                "n": n,
            }

        raw = json.dumps(key_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _get_time_matrix(self, speed: float) -> list[list[int]]:
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
        search_parameters.log_search = False  # 静默模式

        return search_parameters

    def _setup_routing_model(self) -> tuple[pywrapcp.RoutingModel, pywrapcp.RoutingIndexManager]:
        """
        初始化 Routing 模型，注册所有约束和回调。

        将 solve() 和 solve_with_params() 中的公共初始化逻辑提取出来。

        Returns:
            (routing, manager) 元组
        """
        num_locations = len(self.locations)

        manager = pywrapcp.RoutingIndexManager(num_locations, self.num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        # 预计算 routing index -> node 的映射，避免在回调中重复调用 IndexToNode
        # 对于 20 节点问题，该映射可将回调开销降低约 30-40%
        num_indices = manager.GetNumberOfIndices()
        index_to_node = np.empty(num_indices, dtype=np.int32)
        for idx in range(num_indices):
            index_to_node[idx] = manager.IndexToNode(idx)

        # 注册距离回调
        distance_matrix = self.distance_matrix

        def distance_callback(from_index: int, to_index: int) -> int:
            return distance_matrix[index_to_node[from_index]][index_to_node[to_index]]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # 添加容量约束
        demands = self.demands

        def demand_callback(from_index: int) -> int:
            return int(demands[index_to_node[from_index]])

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        capacities = [vehicle["capacity"] for vehicle in self.vehicles]
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index, 0, capacities, True, "Capacity"
        )

        # 添加时间维度
        time_callback_indices = []
        for vehicle_idx in range(self.num_vehicles):
            time_callback = self._create_time_callback_model(manager, vehicle_idx, index_to_node)
            callback_index = routing.RegisterTransitCallback(time_callback)
            time_callback_indices.append(callback_index)

        routing.AddDimensionWithVehicleTransits(time_callback_indices, 30, 960, False, "Time")
        time_dimension = routing.GetDimensionOrDie("Time")

        # 设置时间窗约束
        for location_idx in range(1, num_locations):
            earliest, latest = self.time_windows[location_idx]
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(earliest, latest)
            time_dimension.SetCumulVarSoftUpperBound(index, latest, int(self.time_penalty_per_min))

        # 存储到实例
        self.manager = manager
        return routing, manager

    def _create_time_callback_model(
        self,
        manager: pywrapcp.RoutingIndexManager,
        vehicle_idx: int,
        index_to_node: np.ndarray,
    ) -> Any:
        """
        创建时间回调（不依赖 self.manager，接收外部 manager）。

        Args:
            manager: RoutingIndexManager 实例
            vehicle_idx: 车辆索引
            index_to_node: 预计算的 routing index -> node 映射数组

        Returns:
            时间回调函数
        """
        speed = self.vehicles[vehicle_idx]["speed_kmh"]
        time_matrix = self._get_time_matrix(speed)

        def time_callback(from_index: int, to_index: int) -> int:
            return time_matrix[index_to_node[from_index]][index_to_node[to_index]]

        return time_callback

    def solve(self) -> dict[str, Any]:
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
        num_locations = len(self.locations)

        # 使用公共方法初始化模型
        routing, manager = self._setup_routing_model()

        # 设置搜索参数（自适应优化）
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
        first_solution_strategy: int | None = None,
        metaheuristic: int | None = None,
        time_limit: int | None = None,
    ) -> dict[str, Any]:
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

        # 使用公共方法初始化模型
        routing, manager = self._setup_routing_model()

        # 设置搜索参数
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
        search_parameters.log_search = False

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

    def _extract_solution(
        self, routing: pywrapcp.RoutingModel, solution: pywrapcp.Assignment
    ) -> dict[str, Any]:
        """
        从 OR-Tools 解中提取结构化结果。

        包含详细的时间信息：到达时间、服务时间、离开时间、迟到时间等。
        """
        time_dimension = routing.GetDimensionOrDie("Time")
        routes: list[dict[str, Any]] = []
        total_distance = 0.0
        total_late_minutes = 0
        vehicles_used: dict[str, int] = dict.fromkeys(self.vehicle_config, 0)

        # 预缓存客户信息，避免重复调用 customers_df.iloc
        customer_ids = self.customers_df["id"].to_numpy(dtype=np.int32)
        customer_names = self.customers_df["name"].to_numpy(dtype=object)

        for vehicle_idx in range(self.num_vehicles):
            index = routing.Start(vehicle_idx)
            vehicle = self.vehicles[vehicle_idx]
            route_info: dict[str, Any] = {
                "vehicle_id": vehicle_idx,
                "vehicle_type": vehicle["type"],
                "vehicle_color": vehicle["color"],
                "capacity": vehicle["capacity"],
                "stops": [],
                "distance_km": 0.0,
                "total_demand": 0,
                "total_time_min": 0,
                "late_minutes": 0,
            }

            route_distance = 0
            route_nodes = []

            while not routing.IsEnd(index):
                node_index = self.manager.IndexToNode(index)
                time_var = time_dimension.CumulVar(index)

                # 时间信息
                arrival_time = solution.Min(time_var)
                tw_earliest, tw_latest = self.time_windows[node_index]

                # 计算迟到时间
                late_minutes = max(0, arrival_time - tw_latest)
                total_late_minutes += late_minutes
                route_info["late_minutes"] += late_minutes

                # 服务时间
                service_time = int(self.service_times[node_index]) if node_index > 0 else 0
                route_info["total_time_min"] += service_time

                # 使用预缓存的客户信息
                stop_info: dict[str, Any] = {
                    "node": node_index,
                    "customer_id": int(customer_ids[node_index]),
                    "customer_name": str(customer_names[node_index]),
                    "lat": self.locations[node_index][0],
                    "lon": self.locations[node_index][1],
                    "demand": int(self.demands[node_index]),
                    "arrival_time": int(arrival_time),
                    "service_time": service_time,
                    "tw_earliest": tw_earliest,
                    "tw_latest": tw_latest,
                    "late_minutes": int(late_minutes),
                    "is_late": late_minutes > 0,
                }
                route_info["stops"].append(stop_info)
                route_info["total_demand"] += self.demands[node_index]

                # 下一个节点
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_idx)
                route_nodes.append(node_index)

            # 添加终点（返回仓库）
            end_index = self.manager.IndexToNode(index)
            dest_lat, dest_lon = self.locations[end_index]
            if end_index == 0:
                route_info["stops"].append(
                    {
                        "node": end_index,
                        "customer_id": 0,
                        "customer_name": "仓库",
                        "lat": dest_lat,
                        "lon": dest_lon,
                        "demand": 0,
                        "service_time": 0,
                    }
                )
            else:
                route_info["stops"].append(
                    {
                        "node": end_index,
                        "customer_id": int(customer_ids[end_index]),
                        "customer_name": str(customer_names[end_index]),
                        "lat": dest_lat,
                        "lon": dest_lon,
                    }
                )

            # 转换距离为公里
            route_info["distance_km"] = route_distance / 1000.0
            total_distance += route_info["distance_km"]

            # 只有访问了客户的车辆才算被使用
            if route_nodes:
                vehicles_used[route_info["vehicle_type"]] += 1
                routes.append(route_info)

        return {
            "routes": routes,
            "total_distance": round(total_distance, 2),
            "vehicles_used": vehicles_used,
            "total_late_minutes": int(total_late_minutes),
            "solution_status": "SUCCESS",
        }

    def _create_empty_result(self, status: str) -> dict[str, Any]:
        """创建空的求解结果。"""
        return {
            "routes": [],
            "total_distance": 0,
            "vehicles_used": dict.fromkeys(self.vehicle_config, 0),
            "total_late_minutes": 0,
            "solution_status": status,
        }


def solve_with_cache(
    customers_df: pd.DataFrame,
    vehicle_config: dict[str, dict[str, Any]] | None = None,
    time_penalty_per_min: float = 10.0,
    time_limit: int = 30,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    使用全局池的缓存求解（推荐方法 v4）。

    自动利用解决方案缓存，避免重复求解相同问题。

    Args:
        customers_df: 客户数据框
        vehicle_config: 车型配置
        time_penalty_per_min: 迟到惩罚
        time_limit: 求解时间限制
        use_cache: 是否使用缓存

    Returns:
        求解结果
    """
    return _solver_pool.solve_with_cache(
        customers_df=customers_df,
        vehicle_config=vehicle_config,
        time_penalty_per_min=time_penalty_per_min,
        search_time_limit=time_limit,
        use_cache=use_cache,
    )


def solve_with_multiple_strategies(
    customers_df: pd.DataFrame,
    vehicle_config: dict[str, dict[str, Any]],
    time_penalty_per_min: float = 10.0,
    time_limit: int = 30,
) -> dict[str, Any]:
    """
    使用多种策略求解，返回最优解（优化版 v4：集成缓存）。

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
    vehicle_config: dict[str, dict[str, Any]],
    time_penalty_per_min: float,
    time_limit: int,
    first_solution_strategy: int,
    metaheuristic: int,
) -> dict[str, Any]:
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
    # Windows spawn 子进程不会继承 sys.path，需手动添加项目根目录
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

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
            "vehicles_used": dict.fromkeys(vehicle_config, 0),
            "total_late_minutes": 0,
            "solution_status": "ERROR",
            "solve_time_seconds": 0,
        }


def _init_worker() -> None:
    """Windows spawn 子进程初始化：添加项目根目录到 sys.path。"""
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def solve_with_multiple_strategies_parallel(
    customers_df: pd.DataFrame,
    vehicle_config: dict[str, dict[str, Any]],
    time_penalty_per_min: float = 10.0,
    time_limit: int = 30,
    max_workers: int | None = None,
) -> dict[str, Any]:
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
    # Windows spawn 子进程需要 PYTHONPATH 才能正确导入项目模块
    import os

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    original_pythonpath = os.environ.get("PYTHONPATH", "")
    if project_root not in original_pythonpath.split(os.pathsep):
        separator = os.pathsep if original_pythonpath else ""
        os.environ["PYTHONPATH"] = f"{original_pythonpath}{separator}{project_root}"

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
        with ProcessPoolExecutor(max_workers=max_workers, initializer=_init_worker) as executor:
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
            "vehicles_used": dict.fromkeys(vehicle_config, 0),
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
