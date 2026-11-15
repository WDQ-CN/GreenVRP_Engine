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

import copy
import hashlib
import math
import multiprocessing
import time
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor, TimeoutError, as_completed, wait, FIRST_COMPLETED
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from config.vehicles import DEFAULT_VEHICLE_CONFIG
from config.constants import (
    DEFAULT_LOAD_RATIO,
    DEFAULT_PARAMS,
    DIESEL_CO2_FACTOR,
    FUEL_EMPTY_LOAD_RATIO,
    FUEL_FULL_LOAD_RATIO,
    WORK_DAY_END_MIN,
    WORK_DAY_START_MIN,
)
from logging_config import get_logger

from .distance import DistanceMatrixCache, build_distance_matrix, build_time_matrix
from data_types.solution import SolutionDict
from exceptions.errors import SolverError
from utils.geo import haversine_distance
from utils.time_profile import (
    average_speed_multiplier,
    fuel_speed_factor,
    peak_avoidance_start_minute,
    travel_time_minutes,
)

# 延迟导入 2-opt 后处理器（避免循环依赖）
_route_optimize = None


def _get_route_optimizer():
    """延迟加载 2-opt 后处理器。"""
    global _route_optimize
    if _route_optimize is None:
        from optimization.route_optimize import post_process_solution as _r
        _route_optimize = _r
    return _route_optimize

# 使用统一的日志配置（green_vrp 命名空间确保 SensitiveDataFilter 生效）
logger = get_logger("green_vrp.solver")


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
        fuel_price: float = DEFAULT_PARAMS["fuel_price"],
        carbon_price: float = DEFAULT_PARAMS["carbon_price"],
        vehicle_load_ratios: Optional[List[float]] = None,
        depot_start_minute: Optional[int] = None,
        time_matrix_speed_factor: Optional[float] = None,
        hourly_wage: float = 0.0,
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
            fuel_price: 柴油价格（元/升）
            carbon_price: 碳价（元/kg CO2）
            vehicle_load_ratios: 逐车辆载重率（0~1），用于载重感知二次求解
        """
        self.customers_df = customers_df.copy()
        self.vehicle_config = vehicle_config or DEFAULT_VEHICLE_CONFIG
        self.time_penalty_per_min = time_penalty_per_min
        self.search_time_limit = search_time_limit
        self.use_cache = use_cache
        self.fuel_price = fuel_price
        self.carbon_price = carbon_price
        self.vehicle_load_ratios = vehicle_load_ratios
        self.depot_start_minute = (
            depot_start_minute
            if depot_start_minute is not None
            else WORK_DAY_START_MIN
        )
        self.time_matrix_speed_factor = time_matrix_speed_factor
        self.hourly_wage = max(0.0, float(hourly_wage))

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

        # 预提取列数据为列表（避免 .iloc 循环 O(n²) 性能问题）
        self.demands = self.customers_df["demand"].values.tolist()
        self.service_times = self.customers_df["service_time_min"].values.tolist()
        self.customer_ids = self.customers_df["id"].values.tolist()
        self.customer_names = self.customers_df["name"].values.tolist()
        
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
                vehicle = {
                    "type": v_type,
                    "capacity": config["capacity"],
                    "speed_kmh": config["speed_kmh"],
                    "fixed_cost": config["fixed_cost"],
                    "fuel_per_100km": config["fuel_per_100km"],
                    "color": config["color"],
                }
                for optional_key in ("fuel_empty_per_100km", "fuel_full_per_100km"):
                    if config.get(optional_key) is not None:
                        vehicle[optional_key] = config[optional_key]
                self.vehicles.append(vehicle)
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
            self.fuel_price,
            self.carbon_price,
            tuple(self.vehicle_load_ratios or ()),
            self.depot_start_minute,
            self.time_matrix_speed_factor,
            self.hourly_wage,
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
            # OR-Tools has a static time matrix; the initial solution uses
            # either the duration-weighted average or a caller-provided
            # factor (e.g. 1.0 for the post-peak daytime window).
            speed_factor = (
                self.time_matrix_speed_factor
                if self.time_matrix_speed_factor is not None
                else average_speed_multiplier()
            )
            effective_speed = speed * speed_factor
            self._time_matrix_cache[speed] = build_time_matrix(
                self.distance_matrix, effective_speed
            )
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
            """返回 from_node 服务完成到 to_node 服务开始的耗时（分钟）。"""
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            service_time = int(round(self.service_times[from_node]))
            return time_matrix[from_node][to_node] + service_time

        return time_callback

    def _late_penalty_cents(self) -> int:
        """把用户迟到罚金（元/分钟）换算成目标函数使用的分/分钟。"""
        return max(0, int(round(self.time_penalty_per_min * 100)))

    def _vehicle_cost_per_km_cents(self, vehicle_idx: int) -> float:
        """返回代表载重下车型的燃油 + 碳排成本（分/公里）。"""
        config = self.vehicles[vehicle_idx]
        fuel_per_100km = float(config["fuel_per_100km"])
        fuel_empty_value = config.get("fuel_empty_per_100km")
        fuel_full_value = config.get("fuel_full_per_100km")
        fuel_empty = (
            float(fuel_empty_value)
            if fuel_empty_value is not None
            else fuel_per_100km * FUEL_EMPTY_LOAD_RATIO
        )
        fuel_full = (
            float(fuel_full_value)
            if fuel_full_value is not None
            else fuel_per_100km * FUEL_FULL_LOAD_RATIO
        )
        load_ratio = DEFAULT_LOAD_RATIO
        if (
            self.vehicle_load_ratios is not None
            and 0 <= vehicle_idx < len(self.vehicle_load_ratios)
        ):
            load_ratio = min(
                1.0, max(0.0, float(self.vehicle_load_ratios[vehicle_idx]))
            )
        fuel_at_load = fuel_empty + (fuel_full - fuel_empty) * load_ratio
        # Representative fuel cost includes the average time-of-day speed penalty.
        fuel_at_load *= fuel_speed_factor(average_speed_multiplier())
        unit_cost = (
            max(0.0, self.fuel_price)
            + DIESEL_CO2_FACTOR * max(0.0, self.carbon_price)
        )
        fuel_cost_per_km = fuel_at_load * unit_cost
        if self.hourly_wage > 0:
            speed_factor = (
                self.time_matrix_speed_factor
                if self.time_matrix_speed_factor is not None
                else average_speed_multiplier()
            )
            effective_speed = max(
                float(config["speed_kmh"]) * speed_factor, 0.1
            )
            labor_cost_per_km = self.hourly_wage / effective_speed
            return (fuel_cost_per_km + labor_cost_per_km) * 100.0
        return fuel_cost_per_km

    def _create_cost_callback(self, vehicle_idx: int) -> Callable[[int, int], int]:
        """逐车型弧成本：燃油成本 + 碳排成本（单位：分）。"""
        cost_per_km_cents = self._vehicle_cost_per_km_cents(vehicle_idx)
        if cost_per_km_cents <= 0:
            cost_per_km_cents = 100.0  # 油价/碳价都为 0 时退化为距离最小化

        def cost_callback(from_index: int, to_index: int) -> int:
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            distance_km = self.distance_matrix[from_node][to_node] / 1000.0
            return int(round(distance_km * cost_per_km_cents))

        return cost_callback

    def _set_small_scale_params(
        self, params: pywrapcp.DefaultRoutingSearchParameters, problem_difficulty: float
    ) -> None:
        """小规模（≤20）：使用最精确的策略。"""
        params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        params.time_limit.seconds = int(
            min(self.search_time_limit, 15) * problem_difficulty
        )

    def _set_medium_scale_params(
        self, params: pywrapcp.DefaultRoutingSearchParameters, problem_difficulty: float
    ) -> None:
        """中等规模（21~50）：平衡精度和速度。"""
        params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        params.time_limit.seconds = int(self.search_time_limit * problem_difficulty)

    def _set_large_scale_params(
        self, params: pywrapcp.DefaultRoutingSearchParameters, problem_difficulty: float
    ) -> None:
        """大规模（51~200）：使用更快的方法。"""
        params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        )
        params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH
        )
        params.time_limit.seconds = int(
            max(self.search_time_limit, 60) * problem_difficulty
        )

    def _set_huge_scale_params(
        self, params: pywrapcp.DefaultRoutingSearchParameters, problem_difficulty: float
    ) -> None:
        """超大规模（>200）：并行求解策略 + 增加时间限制。"""
        params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        )
        params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH
        )
        params.time_limit.seconds = int(
            max(self.search_time_limit * 2, 120) * problem_difficulty
        )

    def _get_adaptive_search_params(
        self, num_locations: int, problem_difficulty: float = 1.0
    ) -> pywrapcp.DefaultRoutingSearchParameters:
        """
        根据问题规模自适应调整搜索参数（v4优化版）。

        小规模问题使用更精确的搜索策略，
        大规模问题使用更快的启发式方法。
        v4新增：规模自适应的 GLS lambda、LNS 时限、二次清理比例

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
            self._set_small_scale_params(search_parameters, problem_difficulty)
            # 小规模：利用更多，快速收敛
            search_parameters.guided_local_search_lambda_coefficient = 0.2
            search_parameters.lns_time_limit.seconds = 0
            search_parameters.secondary_ls_time_limit_ratio = 0.1
        elif effective_size <= 50:
            self._set_medium_scale_params(search_parameters, problem_difficulty)
            # 中等规模：平衡探索与利用
            search_parameters.guided_local_search_lambda_coefficient = 0.5
            search_parameters.lns_time_limit.seconds = 5
            search_parameters.secondary_ls_time_limit_ratio = 0.08
        elif effective_size <= 200:
            self._set_large_scale_params(search_parameters, problem_difficulty)
            # 大规模：偏向探索
            search_parameters.guided_local_search_lambda_coefficient = 0.8
            search_parameters.lns_time_limit.seconds = 10
            search_parameters.secondary_ls_time_limit_ratio = 0.05
        else:
            self._set_huge_scale_params(search_parameters, problem_difficulty)
            # 超大规模：高探索 + 限制 LNS 单次时间
            search_parameters.guided_local_search_lambda_coefficient = 1.0
            search_parameters.lns_time_limit.seconds = 15
            search_parameters.secondary_ls_time_limit_ratio = 0.05

        # 通用优化参数
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

        # 注册逐车型成本回调：固定成本 + 燃油成本 + 碳排成本
        for vehicle_idx in range(self.num_vehicles):
            cost_callback = self._create_cost_callback(vehicle_idx)
            cost_callback_index = routing.RegisterTransitCallback(cost_callback)
            routing.SetArcCostEvaluatorOfVehicle(cost_callback_index, vehicle_idx)
            fixed_cost_cents = int(
                round(float(self.vehicles[vehicle_idx]["fixed_cost"]) * 100)
            )
            routing.SetFixedCostOfVehicle(fixed_cost_cents, vehicle_idx)

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
            max(WORK_DAY_END_MIN, 960),  # 时间范围上界（使用工作日结束时间）
            False,  # 不强制从零开始
            "Time",
        )
        time_dimension = routing.GetDimensionOrDie("Time")
        time_upper_bound = max(WORK_DAY_END_MIN, 960)

        # 车辆从工作日开始时间出发，避免求解器通过提前发车绕过时间窗
        for vehicle_idx in range(self.num_vehicles):
            start_index = routing.Start(vehicle_idx)
            time_dimension.CumulVar(start_index).SetRange(
                self.depot_start_minute, time_upper_bound
            )

        # 设置时间窗约束（跳过仓库）
        # 注：SetRange 的上界必须宽于 SetCumulVarSoftUpperBound，
        # 否则软惩罚无法生效（硬约束会阻止变量超出 latest）
        # 同时上界不能超过时间维度的上界
        late_penalty_cents = self._late_penalty_cents()
        for location_idx in range(1, num_locations):
            earliest, latest = self.time_windows[location_idx]
            index = self.manager.NodeToIndex(location_idx)
            # 硬约束只限制不早于 earliest；迟到由用户罚金软约束控制
            time_dimension.CumulVar(index).SetRange(earliest, time_upper_bound)
            time_dimension.SetCumulVarSoftUpperBound(
                index, latest, late_penalty_cents
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
                          departure_time: int, late_minutes: int,
                          raw_arrival_time: Optional[int] = None) -> Dict[str, Any]:
        """构建单站点的数据结构（使用预提取数组避免 .iloc O(n) 调用）。"""
        return {
            "node": node_index,
            "customer_id": int(self.customer_ids[node_index]),
            "customer_name": str(self.customer_names[node_index]),
            "lat": self.locations[node_index][0],
            "lon": self.locations[node_index][1],
            "demand": int(self.demands[node_index]),
            "raw_arrival_time": int(
                arrival_time if raw_arrival_time is None else raw_arrival_time
            ),
            "arrival_time": int(arrival_time),
            "departure_time": int(departure_time),
            "service_time": self.service_times[node_index] if node_index > 0 else 0,
            "tw_earliest": int(self.time_windows[node_index][0]),
            "tw_latest": int(self.time_windows[node_index][1]),
            "late_minutes": int(late_minutes),
            "is_late": late_minutes > 0,
        }

    def _build_depot_stop(
        self, end_index: int, arrival_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """构建路线终点（仓库）的数据结构。"""
        if end_index == 0:
            stop = {
                "node": end_index,
                "customer_id": None,  # 仓库不是客户
                "customer_name": "仓库",
                "lat": self.locations[end_index][0],
                "lon": self.locations[end_index][1],
                "demand": 0,
                "service_time": 0,
            }
        else:
            # 非0索引说明路线未正常结束，但仍记录
            stop = {
                "node": end_index,
                "customer_id": int(self.customer_ids[end_index]),
                "customer_name": str(self.customer_names[end_index]),
                "lat": self.locations[end_index][0],
                "lon": self.locations[end_index][1],
            }
        if arrival_time is not None:
            stop["raw_arrival_time"] = int(arrival_time)
            stop["arrival_time"] = int(arrival_time)
            stop["departure_time"] = int(arrival_time)
        return stop

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
        speed_kmh = self.vehicles[vehicle_idx]["speed_kmh"]
        start_time = solution.Min(time_dimension.CumulVar(index))
        clock = start_time
        previous_node: Optional[int] = None

        while not routing.IsEnd(index):
            node_index = self.manager.IndexToNode(index)
            service_time = int(round(self.service_times[node_index])) if node_index > 0 else 0

            if previous_node is None:
                raw_arrival_time = clock
                arrival_time = clock
            else:
                leg_km = (
                    self.distance_matrix[previous_node][node_index] / 1000.0
                )
                raw_arrival_time = clock + travel_time_minutes(
                    leg_km, clock, speed_kmh
                )
                arrival_time = raw_arrival_time
                earliest = self.time_windows[node_index][0]
                if arrival_time < earliest:
                    arrival_time = earliest

            _, tw_latest = self.time_windows[node_index]
            late_minutes = max(0, arrival_time - tw_latest) if node_index > 0 else 0
            vehicle_late += late_minutes

            departure_time = arrival_time + service_time
            stop_info = self._build_stop_info(
                node_index,
                arrival_time,
                departure_time,
                late_minutes,
                raw_arrival_time=raw_arrival_time,
            )
            route_info["stops"].append(stop_info)
            route_info["total_demand"] += self.demands[node_index]
            route_info["late_minutes"] += late_minutes

            next_index = solution.Value(routing.NextVar(index))
            next_node = self.manager.IndexToNode(next_index)
            route_distance += self.distance_matrix[node_index][next_node]
            index = next_index
            route_nodes.append(node_index)
            previous_node = node_index
            clock = departure_time

        # 添加终点（返回仓库）
        end_index = self.manager.IndexToNode(index)
        end_time = clock
        if previous_node is not None:
            return_km = self.distance_matrix[previous_node][end_index] / 1000.0
            end_time += travel_time_minutes(return_km, clock, speed_kmh)
        route_info["stops"].append(self._build_depot_stop(end_index, end_time))
        route_info["distance_km"] = route_distance / 1000.0
        route_info["total_time_min"] = max(0, int(end_time - start_time))

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

            if any(node != 0 for node in route_nodes):
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


def _get_default_strategies() -> List[Tuple[int, int]]:
    """获取默认求解策略组合列表（5种策略，覆盖更广的搜索空间）。"""
    return [
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
        (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
            routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT,
        ),
        (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
        ),
    ]


def _select_best_solution(
    results: List[Dict[str, Any]],
    vehicle_config: Optional[Dict[str, Dict[str, Any]]] = None,
    cost_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    从多个求解结果中选择最优解。

    提供 vehicle_config 和 cost_params 时，按完整五维成本（燃油、碳排、
    人工、固定、违约）择优；否则回退到轻量距离评分（兼容旧调用）。
    """
    best_solution = None
    best_score = float("inf")
    use_cost = vehicle_config is not None and cost_params is not None
    cost_fn = None
    if use_cost:
        try:
            from .cost import calculate_green_cost
            cost_fn = calculate_green_cost
        except Exception as e:
            logger.warning("成本择优不可用，回退轻量评分: %s", e)
            use_cost = False

    for result in results:
        if result["solution_status"] != "SUCCESS":
            continue

        score = None
        if use_cost and cost_fn is not None:
            try:
                score = cost_fn(result, vehicle_config, cost_params)["total_cost"]
            except Exception as e:
                logger.debug("候选解成本计算失败，回退轻量评分: %s", e)

        if score is None:
            vehicles = sum(result.get("vehicles_used", {}).values())
            score = (
                result["total_distance"]
                + result["total_late_minutes"] * 0.5
                + vehicles * 5.0
            )

        if score < best_score:
            best_score = score
            best_solution = result

    return best_solution


def _rank_stages_with_probe(
    results: List[Dict[str, Any]],
    vehicle_config: Optional[Dict[str, Dict[str, Any]]] = None,
    cost_params: Optional[Dict[str, Any]] = None,
    customer_count: int = 0,
    probe_count: int = 3,
    probe_iterations: int = 300,
    probe_seed: int = 42,
    probe_temperature: float = 0.02,
) -> List[Tuple[float, Dict[str, Any]]]:
    """用短 ALNS 探针为首版解排序，供多路径精修使用。"""
    if customer_count < 20 or len(results) <= 1 or vehicle_config is None:
        best = _select_best_solution(results, vehicle_config, cost_params)
        return [(float("inf"), best)] if best is not None else []
    if cost_params is None:
        best = _select_best_solution(results, vehicle_config, cost_params)
        return [(float("inf"), best)] if best is not None else []

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for result in results:
        if result.get("solution_status") != "SUCCESS":
            continue
        cost = _solution_total_cost(result, vehicle_config, cost_params)
        if cost is not None:
            scored.append((cost, result))
    if not scored:
        return []
    if len(scored) == 1:
        return [(scored[0][0], scored[0][1])]
    scored.sort(key=lambda item: item[0])

    try:
        from optimization.alns import improve_solution_with_alns
    except Exception:
        return scored

    probe_params = {
        **cost_params,
        "alns_base_start_minute": peak_avoidance_start_minute(),
        "alns_iteration_limit": max(100, int(probe_iterations)),
        "alns_temperature_ratio": probe_temperature,
    }
    ranked: List[Tuple[float, Dict[str, Any]]] = []
    for initial_cost, result in scored[: max(1, probe_count)]:
        try:
            probed = improve_solution_with_alns(
                result,
                vehicle_config,
                probe_params,
                time_limit=15.0,
                seed=probe_seed,
            )
            probed_cost = _solution_total_cost(
                probed, vehicle_config, cost_params
            )
            if probed_cost is None or not _solution_fits_fleet(
                probed, vehicle_config
            ):
                probed = result
                probed_cost = initial_cost
        except Exception:
            probed = result
            probed_cost = initial_cost
        ranked.append((probed_cost, probed))

    ranked.sort(key=lambda item: item[0])
    if ranked:
        logger.info(
            "首版解 ALNS 探针排序: %d 个候选, 最优成本 %.2f",
            len(ranked),
            ranked[0][0],
        )
    return ranked


def _select_stage_with_probe(
    results: List[Dict[str, Any]],
    vehicle_config: Optional[Dict[str, Dict[str, Any]]] = None,
    cost_params: Optional[Dict[str, Any]] = None,
    customer_count: int = 0,
    probe_count: int = 3,
    probe_iterations: int = 300,
    probe_seed: int = 42,
    probe_temperature: float = 0.02,
) -> Optional[Dict[str, Any]]:
    """用短 ALNS 探针选择首版解，避免只看优化前成本选错盆地。"""
    ranked = _rank_stages_with_probe(
        results,
        vehicle_config,
        cost_params,
        customer_count,
        probe_count,
        probe_iterations,
        probe_seed,
        probe_temperature,
    )
    if not ranked:
        return _select_best_solution(results, vehicle_config, cost_params)
    return ranked[0][1]


def _effective_vehicle_load_ratios(
    solution: Dict[str, Any],
    vehicle_config: Dict[str, Dict[str, Any]],
) -> List[float]:
    """按上一轮路线计算每辆车的距离加权平均载重率。"""
    vehicle_types: List[str] = []
    for v_type, config in vehicle_config.items():
        vehicle_types.extend([v_type] * int(config.get("count", 0)))

    ratios = [DEFAULT_LOAD_RATIO] * len(vehicle_types)
    if not ratios:
        return ratios

    for route in solution.get("routes", []):
        try:
            vehicle_id = int(route.get("vehicle_id", -1))
        except (TypeError, ValueError):
            continue
        if vehicle_id < 0 or vehicle_id >= len(ratios):
            continue

        stops = route.get("stops", [])
        if not isinstance(stops, (list, tuple)) or len(stops) < 2:
            continue
        if any(
            not isinstance(stop, dict) or "lat" not in stop or "lon" not in stop
            for stop in stops
        ):
            continue

        capacity = route.get("capacity")
        if capacity is None:
            capacity = vehicle_config.get(vehicle_types[vehicle_id], {}).get(
                "capacity", 0
            )
        try:
            capacity = float(capacity)
        except (TypeError, ValueError):
            capacity = 0.0
        if capacity <= 0:
            continue

        total_demand = sum(
            float(stop.get("demand", 0) or 0)
            for stop in stops
            if (stop.get("node") or 0) > 0
        )
        if total_demand <= 0:
            continue

        load = total_demand
        weighted_ratio = 0.0
        total_km = 0.0
        for index in range(len(stops) - 1):
            from_stop = stops[index]
            to_stop = stops[index + 1]
            if (from_stop.get("node") or 0) > 0:
                load = max(0.0, load - float(from_stop.get("demand", 0) or 0))

            leg_km = haversine_distance(
                from_stop["lat"],
                from_stop["lon"],
                to_stop["lat"],
                to_stop["lon"],
            )
            weighted_ratio += leg_km * min(1.0, max(0.0, load / capacity))
            total_km += leg_km

        if total_km > 0:
            ratios[vehicle_id] = weighted_ratio / total_km

    return ratios


def _fleet_capacity(vehicle_config: Dict[str, Dict[str, Any]]) -> float:
    """车队总容量。"""
    return sum(
        float(config.get("capacity", 0)) * int(config.get("count", 0))
        for config in vehicle_config.values()
    )


def _solution_fits_fleet(
    solution: Dict[str, Any],
    vehicle_config: Dict[str, Dict[str, Any]],
) -> bool:
    """校验解的车辆类型与数量不超过车队配置。"""
    counts: Dict[str, int] = {}
    seen_vehicle_ids = set()
    for route in solution.get("routes", []):
        vehicle_type = route.get("vehicle_type")
        if vehicle_type not in vehicle_config:
            return False
        vehicle_id = route.get("vehicle_id")
        if vehicle_id is not None:
            if vehicle_id in seen_vehicle_ids:
                return False
            seen_vehicle_ids.add(vehicle_id)
        counts[vehicle_type] = counts.get(vehicle_type, 0) + 1
    return all(
        count <= int(vehicle_config[vehicle_type].get("count", 0))
        for vehicle_type, count in counts.items()
    )


def _try_fleet_reduction(
    solution: Dict[str, Any],
    customers_df: pd.DataFrame,
    vehicle_config: Dict[str, Dict[str, Any]],
    time_penalty_per_min: float,
    fuel_price: float,
    carbon_price: float,
    time_limit: int,
    cost_params: Dict[str, Any],
    stage_fuel_price: Optional[float] = None,
) -> List[Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], float]]:
    """尝试减少一辆车重新求解，返回全部可行候选及其五维成本。

    仅在当前解已用满全部车辆时触发；容量不足的候选会被跳过。
    """
    if len(customers_df) - 1 < 20 or time_limit < 10:
        return []

    try:
        total_demand = float(
            pd.to_numeric(customers_df["demand"], errors="coerce").fillna(0).sum()
        )
    except Exception:
        return []
    if total_demand <= 0:
        return []

    total_vehicles = sum(
        int(config.get("count", 0)) for config in vehicle_config.values()
    )
    used_vehicles = sum(
        int(count or 0)
        for count in (solution.get("vehicles_used", {}) or {}).values()
    )
    if used_vehicles < total_vehicles:
        return []

    candidates: List[Tuple[float, str, Dict[str, Dict[str, Any]]]] = []
    for vehicle_type, config in vehicle_config.items():
        count = int(config.get("count", 0))
        if count <= 0:
            continue
        reduced = {
            name: dict(values) for name, values in vehicle_config.items()
        }
        reduced[vehicle_type]["count"] = count - 1
        if _fleet_capacity(reduced) + 1e-9 < total_demand:
            continue
        candidates.append(
            (
                float(config.get("fixed_cost", 0.0)),
                vehicle_type,
                reduced,
            )
        )
    if not candidates:
        return []
    candidates.sort(key=lambda item: -item[0])

    fleet_time = max(20, min(45, int(time_limit)))
    results: List[Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], float]] = []

    for _removed_fixed, vehicle_type, reduced_config in candidates[:2]:
        try:
            solver = GreenVRPSolver(
                customers_df=customers_df,
                vehicle_config=reduced_config,
                time_penalty_per_min=time_penalty_per_min,
                search_time_limit=fleet_time,
                fuel_price=(
                    stage_fuel_price
                    if stage_fuel_price is not None
                    else fuel_price
                ),
                carbon_price=carbon_price,
            )
            candidate = solver.solve_with_params(
                first_solution_strategy=(
                    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
                ),
                metaheuristic=(
                    routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
                ),
                time_limit=fleet_time,
            )
        except Exception as e:
            logger.warning(
                "缩减车型 %s 求解失败: %s", vehicle_type, str(e)[:200]
            )
            continue

        if (
            candidate.get("solution_status") != "SUCCESS"
            or not candidate.get("routes")
        ):
            logger.info("缩减车型 %s 无可行解", vehicle_type)
            continue

        try:
            candidate = _get_route_optimizer()(candidate, reduced_config)
        except Exception as e:
            logger.warning(
                "缩减车型 %s 后处理失败: %s", vehicle_type, str(e)[:200]
            )

        candidate_cost = _solution_total_cost(
            candidate, reduced_config, cost_params
        )
        if candidate_cost is None:
            continue
        logger.info(
            "缩减 %s 候选: 成本 %.2f, 路线 %d 条",
            vehicle_type,
            candidate_cost,
            len(candidate.get("routes", [])),
        )
        results.append((candidate, reduced_config, candidate_cost))
        # 优先移除固定成本最高的车型；找到第一个可行候选即可，
        # 避免把时间浪费在明显更差的保留大车方案上。
        break

    results.sort(key=lambda item: item[2])
    return results


def _solution_total_cost(
    solution: Dict[str, Any],
    vehicle_config: Dict[str, Dict[str, Any]],
    cost_params: Dict[str, Any],
) -> Optional[float]:
    """计算候选解的五维总成本，失败时返回 None。"""
    try:
        from .cost import calculate_green_cost

        return float(
            calculate_green_cost(solution, vehicle_config, cost_params)["total_cost"]
        )
    except Exception as e:
        logger.debug("候选解成本计算失败: %s", e)
        return None


def _alns_seed_worker(
    solution: Dict[str, Any],
    config: Dict[str, Dict[str, Any]],
    params: Dict[str, Any],
    time_limit: float,
    seed: int,
    recombine: bool,
    recombine_time: float,
) -> Dict[str, Any]:
    """多进程 ALNS 单种子工作函数。"""
    from optimization.alns import improve_solution_with_alns

    return improve_solution_with_alns(
        solution,
        config,
        params,
        time_limit=time_limit,
        seed=seed,
        recombine=recombine,
        recombine_time=recombine_time,
    )


def _recombine_seed_solutions(
    solutions: List[Dict[str, Any]],
    base_solution: Dict[str, Any],
    config: Dict[str, Dict[str, Any]],
    params: Dict[str, Any],
    time_limit: float = 5.0,
    extra_pools: Optional[List[Dict[Any, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """用多个种子的优质路线做集合划分重组。"""
    from optimization.alns import (
        RouteState,
        _ALNSOptimizer,
        _build_solution,
        _build_vehicle_pool,
        _extract_initial,
    )
    from optimization.recombine import recombine_route_pool

    pool = _build_vehicle_pool(config)
    routes, available, depot = _extract_initial(base_solution, pool)
    if routes is None or available is None or depot is None:
        return None

    optimizer = _ALNSOptimizer(
        routes, available, depot, config, params, seed=0
    )
    for solution in solutions:
        for route in solution.get("routes", []):
            vehicle = optimizer.vehicle_by_type.get(route.get("vehicle_type"))
            if vehicle is None:
                continue
            stops = route.get("stops", [])
            customers = [
                stop
                for stop in stops
                if stop.get("customer_id") not in (0, None)
            ]
            if not customers:
                continue
            start_minute = int(stops[0].get("arrival_time", WORK_DAY_START_MIN))
            optimizer._record_pool(
                [
                    RouteState(
                        vehicle, customers, start_minute=start_minute
                    )
                ]
            )

    for pool in extra_pools or []:
        for (vehicle_type, _sorted_ids), value in pool.items():
            ids, metrics, start_minute = value
            if not math.isfinite(metrics.cost):
                continue
            vehicle = optimizer.vehicle_by_type.get(vehicle_type)
            if vehicle is None:
                continue
            if any(cid not in optimizer.customer_by_id for cid in ids):
                continue
            extra_route = RouteState(
                vehicle,
                [
                    optimizer.customer_by_id[cid]
                    for cid in ids
                ],
                start_minute=int(start_minute),
            )
            # 用精确发车时刻修正池路线的成本口径
            optimizer.optimize_start_times([extra_route])
            optimizer._record_pool([extra_route])

    result = recombine_route_pool(optimizer, time_limit=time_limit)
    if result is None:
        return None
    selected, _ = result
    optimizer.optimize_start_times(selected)
    selected = [
        optimizer._polish_route(route, max_passes=4) for route in selected
    ]
    optimizer.optimize_start_times(selected)
    return _build_solution(selected, config, depot, base_solution, 0.0)


def _two_opt_star_polish(
    solution: Dict[str, Any],
    config: Dict[str, Dict[str, Any]],
    params: Dict[str, Any],
    time_limit: float = 15.0,
    include_segment: bool = False,
    include_pairwise: bool = False,
) -> Optional[Dict[str, Any]]:
    """对最终解做跨路线 2-opt* 尾部交换后处理。"""
    from optimization.alns import (
        RouteState,
        _ALNSOptimizer,
        _build_solution,
        _build_vehicle_pool,
    )

    pool = _build_vehicle_pool(config)
    by_id = {vehicle.vehicle_id: vehicle for vehicle in pool}
    by_type: Dict[str, Any] = {}
    for vehicle in pool:
        by_type.setdefault(vehicle.vehicle_type, vehicle)

    routes = []
    depot: Optional[Dict[str, Any]] = None
    used_ids = set()
    for route in solution.get("routes", []):
        stops = route.get("stops", [])
        if not stops:
            continue
        for stop in stops:
            if stop.get("customer_id") == 0 or stop.get("node") == 0:
                depot = stop
                break
        customers = [
            stop
            for stop in stops
            if stop.get("customer_id") not in (0, None)
        ]
        if not customers:
            continue
        vehicle = by_id.get(route.get("vehicle_id"))
        if vehicle is None:
            vehicle = by_type.get(route.get("vehicle_type"))
        if vehicle is None:
            continue
        used_ids.add(vehicle.vehicle_id)
        start_minute = int(
            stops[0].get("arrival_time", WORK_DAY_START_MIN)
        )
        routes.append(
            RouteState(vehicle, customers, start_minute=start_minute)
        )

    if not routes or depot is None:
        return None

    available = [
        vehicle for vehicle in pool if vehicle.vehicle_id not in used_ids
    ]
    optimizer = _ALNSOptimizer(
        routes, available, depot, config, params, seed=0
    )
    optimizer.optimize_start_times(routes)
    started = time.perf_counter()
    if include_segment:
        moves = optimizer.two_opt_star(routes, time_limit * 0.34)
        vnd_moves = optimizer.inter_route_vnd(routes, time_limit * 0.33)
        segment_moves = optimizer.inter_route_segment_vnd(
            routes, time_limit * 0.33
        )
    else:
        moves = optimizer.two_opt_star(routes, time_limit * 0.5)
        vnd_moves = optimizer.inter_route_vnd(routes, time_limit * 0.5)
        segment_moves = 0
    pair_moves = 0
    if include_pairwise:
        pair_moves = optimizer.pairwise_alns(routes, 300)
    if moves + vnd_moves + segment_moves + pair_moves == 0:
        return None
    logger.info(
        "2-opt* / VND / 段搬移 / 配对ALNS: %d + %d + %d + %d 次交换",
        moves,
        vnd_moves,
        segment_moves,
        pair_moves,
    )
    return _build_solution(
        routes,
        config,
        depot,
        solution,
        time.perf_counter() - started,
    )


def _cpsat_pair_polish(
    solution: Dict[str, Any],
    config: Dict[str, Dict[str, Any]],
    params: Dict[str, Any],
    time_limit_per_pair: float = 8.0,
) -> Optional[Dict[str, Any]]:
    """对最终解逐对做 CP-SAT 精确重排。"""
    from optimization.alns import (
        _ALNSOptimizer,
        _build_solution,
        _build_vehicle_pool,
        _extract_initial,
    )
    from optimization.pair_cpsat import improve_pairs_with_cpsat

    pool = _build_vehicle_pool(config)
    routes, available, depot = _extract_initial(solution, pool)
    if routes is None or available is None or depot is None:
        return None
    optimizer = _ALNSOptimizer(
        routes, available, depot, config, params, seed=0
    )
    optimizer.optimize_start_times(routes)
    started = time.perf_counter()
    moves = improve_pairs_with_cpsat(
        optimizer, routes, depot, time_limit_per_pair
    )
    if moves == 0:
        return None
    logger.info("CP-SAT 配对重排生效: %d 对路线", moves)
    return _build_solution(
        routes,
        config,
        depot,
        solution,
        time.perf_counter() - started,
    )


def _run_alns_portfolio(
    entries: List[Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]],
    params: Dict[str, Any],
    alns_time: float,
    seed: int = 42,
    recombine: bool = False,
    recombine_time: float = 5.0,
    seeds: Optional[Sequence[int]] = None,
    seed_params: Optional[Sequence[Optional[Dict[str, Any]]]] = None,
    priority_runs: Optional[
        Sequence[Tuple[int, Optional[Dict[str, Any]]]]
    ] = None,
    cross_recombine: bool = False,
    cross_recombine_time: float = 5.0,
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """对多个候选解做 ALNS 探针，再把剩余时间投入最优候选。"""
    from optimization.alns import improve_solution_with_alns

    run_seeds = list(seeds) if seeds else [seed]
    run_params = []
    for index, _run_seed in enumerate(run_seeds):
        override = (
            seed_params[index]
            if seed_params is not None and index < len(seed_params)
            else None
        )
        run_params.append({**params, **override} if override else params)

    if len(entries) == 1:
        solution, config = entries[0]
        candidates: List[Tuple[int, Dict[str, Any]]] = []
        priority_pools: List[Dict[Any, Any]] = []

        for priority_seed, priority_override in priority_runs or ():
            try:
                priority_params = (
                    {**params, **priority_override}
                    if priority_override
                    else params
                )
                pool_out: Dict[Any, Any] = {}
                candidate = improve_solution_with_alns(
                    solution,
                    config,
                    priority_params,
                    time_limit=alns_time,
                    seed=priority_seed,
                    recombine=recombine,
                    recombine_time=recombine_time,
                    route_pool_out=pool_out,
                )
                candidates.append((priority_seed, candidate))
                if pool_out:
                    priority_pools.append(pool_out)
            except Exception as e:
                logger.warning(
                    "ALNS 优先种子 %d 失败: %s",
                    priority_seed,
                    str(e)[:200],
                )

        if len(run_seeds) == 1:
            candidates.append(
                (
                    run_seeds[0],
                    improve_solution_with_alns(
                        solution,
                        config,
                        run_params[0],
                        time_limit=alns_time,
                        seed=run_seeds[0],
                        recombine=recombine,
                        recombine_time=recombine_time,
                    ),
                )
            )
        else:
            from concurrent.futures import ProcessPoolExecutor, as_completed

            workers = min(len(run_seeds), multiprocessing.cpu_count())
            try:
                with ProcessPoolExecutor(max_workers=workers) as executor:
                    futures = {
                        executor.submit(
                            _alns_seed_worker,
                            solution,
                            config,
                            params_for_seed,
                            alns_time,
                            run_seed,
                            recombine,
                            recombine_time,
                        ): run_seed
                        for run_seed, params_for_seed in zip(
                            run_seeds, run_params
                        )
                    }
                    for future in as_completed(futures):
                        run_seed = futures[future]
                        try:
                            candidates.append((run_seed, future.result()))
                        except Exception as e:
                            logger.warning(
                                "ALNS 种子 %d 失败: %s",
                                run_seed,
                                str(e)[:200],
                            )
            except Exception as e:
                logger.warning(
                    "ALNS 多进程失败，回退串行: %s", str(e)[:200]
                )

            if not candidates:
                for run_seed, params_for_seed in zip(
                    run_seeds, run_params
                ):
                    candidates.append(
                        (
                            run_seed,
                            improve_solution_with_alns(
                                solution,
                                config,
                                params_for_seed,
                                time_limit=alns_time,
                                seed=run_seed,
                                recombine=recombine,
                                recombine_time=recombine_time,
                            ),
                        )
                    )

        best_solution: Optional[Dict[str, Any]] = None
        best_cost = float("inf")
        scored_candidates: List[
            Tuple[float, int, Dict[str, Any]]
        ] = []
        for run_seed, candidate in candidates:
            candidate_cost = _solution_total_cost(candidate, config, params)
            logger.info(
                "ALNS 种子 %d: 成本 %s",
                run_seed,
                f"{candidate_cost:.2f}" if candidate_cost is not None else "N/A",
            )
            if candidate_cost is not None:
                scored_candidates.append(
                    (candidate_cost, run_seed, candidate)
                )
            if candidate_cost is not None and candidate_cost < best_cost:
                best_cost = candidate_cost
                best_solution = candidate
        if best_solution is None:
            return entries[0]
        if cross_recombine and len(scored_candidates) > 1:
            try:
                scored_candidates.sort(key=lambda item: item[0])
                for cost, run_seed, candidate in scored_candidates[:3]:
                    polished = _two_opt_star_polish(
                        candidate, config, params, 5.0
                    )
                    if polished is None:
                        continue
                    polished_cost = _solution_total_cost(
                        polished, config, params
                    )
                    if polished_cost is None or polished_cost >= cost - 1e-6:
                        continue
                    for index, entry in enumerate(scored_candidates):
                        if entry[2] is candidate:
                            scored_candidates[index] = (
                                polished_cost,
                                run_seed,
                                polished,
                            )
                            break
                    if polished_cost < best_cost - 1e-6:
                        best_solution = polished
                        best_cost = polished_cost
                        logger.info(
                            "重组前种子精修生效: %.2f -> %.2f",
                            cost,
                            polished_cost,
                        )
                combined = _recombine_seed_solutions(
                    [candidate for _, _, candidate in scored_candidates],
                    best_solution,
                    config,
                    params,
                    time_limit=cross_recombine_time,
                    extra_pools=priority_pools,
                )
                if combined is not None:
                    combined_cost = _solution_total_cost(
                        combined, config, params
                    )
                    if (
                        combined_cost is not None
                        and combined_cost < best_cost - 1e-6
                    ):
                        logger.info(
                            "跨种子路线重组生效: %.2f -> %.2f",
                            best_cost,
                            combined_cost,
                        )
                        best_solution = combined
                        best_cost = combined_cost
            except Exception as e:
                logger.warning(
                    "跨种子路线重组失败: %s", str(e)[:200]
                )
        logger.info("ALNS 多种子最优: %.2f", best_cost)
        return best_solution, config

    probe_time = max(8.0, min(15.0, alns_time * 0.12))
    best_solution: Optional[Dict[str, Any]] = None
    best_config: Optional[Dict[str, Dict[str, Any]]] = None
    best_cost = float("inf")

    for index, (solution, config) in enumerate(entries):
        candidate = improve_solution_with_alns(
            solution,
            config,
            params,
            time_limit=probe_time,
            seed=seed,
            recombine=recombine,
            recombine_time=recombine_time,
        )
        candidate_cost = _solution_total_cost(candidate, config, params)
        logger.info(
            "ALNS 候选 %d 探针: 成本 %s",
            index,
            f"{candidate_cost:.2f}" if candidate_cost is not None else "N/A",
        )
        if candidate_cost is not None and candidate_cost < best_cost:
            best_cost = candidate_cost
            best_solution = candidate
            best_config = config

    remaining = alns_time - probe_time * len(entries)
    if remaining >= 5.0 and best_solution is not None and best_config is not None:
        candidate = improve_solution_with_alns(
            best_solution,
            best_config,
            params,
            time_limit=remaining,
            seed=seed + 1,
            recombine=recombine,
            recombine_time=recombine_time,
        )
        candidate_cost = _solution_total_cost(candidate, best_config, params)
        if candidate_cost is not None and candidate_cost < best_cost - 1e-6:
            best_solution = candidate
            best_cost = candidate_cost

    if best_solution is None or best_config is None:
        return entries[0]
    logger.info("ALNS 组合最优候选: %.2f", best_cost)
    return best_solution, best_config


def refine_solution_with_load_ratios(
    stage1: Dict[str, Any],
    customers_df: pd.DataFrame,
    vehicle_config: Dict[str, Dict[str, Any]],
    time_penalty_per_min: float = 10.0,
    fuel_price: float = DEFAULT_PARAMS["fuel_price"],
    carbon_price: float = DEFAULT_PARAMS["carbon_price"],
    time_limit: int = 30,
    cost_params: Optional[Dict[str, Any]] = None,
    post_process_stage1: bool = False,
    use_alns: bool = True,
    try_fleet_reduction: bool = True,
    stage_fuel_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    两阶段载重感知优化 + ALNS 后优化。

    1. 从首轮解提取每辆车的距离加权平均载重率。
    2. 用这些载重率重建逐车型弧成本并二次求解。
    3. 对二次解做后处理，按真实五维成本保留更优解。
    4. 在最终解上运行自适应大邻域搜索（IALNS/ALNS），再按真实成本择优。
    """
    if stage1.get("solution_status") != "SUCCESS" or not stage1.get("routes"):
        return stage1

    if post_process_stage1:
        try:
            stage1 = _get_route_optimizer()(stage1, vehicle_config)
        except Exception as e:
            logger.warning(
                "首轮后处理失败: %s", str(e)[:200] if e else "未知错误"
            )

    params = {**DEFAULT_PARAMS, **(cost_params or {})}
    params["late_penalty_per_min"] = time_penalty_per_min
    params["fuel_price"] = fuel_price
    params["carbon_price"] = carbon_price

    best_solution = stage1
    ratios = _effective_vehicle_load_ratios(stage1, vehicle_config)
    if ratios and any(
        abs(ratio - DEFAULT_LOAD_RATIO) > 0.02 for ratio in ratios
    ):
        refinement_time = max(5, min(time_limit // 3, 30))
        try:
            refined_solver = GreenVRPSolver(
                customers_df=customers_df,
                vehicle_config=vehicle_config,
                time_penalty_per_min=time_penalty_per_min,
                search_time_limit=refinement_time,
                fuel_price=(
                    stage_fuel_price
                    if stage_fuel_price is not None
                    else fuel_price
                ),
                carbon_price=carbon_price,
                vehicle_load_ratios=ratios,
            )
            stage2 = refined_solver.solve_with_params(
                first_solution_strategy=(
                    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
                ),
                metaheuristic=(
                    routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
                ),
                time_limit=refinement_time,
            )
        except Exception as e:
            logger.warning(
                "载重感知二次求解失败: %s", str(e)[:200] if e else "未知错误"
            )
            stage2 = None

        if stage2 and stage2.get("solution_status") == "SUCCESS" and stage2.get("routes"):
            try:
                stage2 = _get_route_optimizer()(stage2, vehicle_config)
            except Exception as e:
                logger.warning(
                    "二次解后处理失败: %s", str(e)[:200] if e else "未知错误"
                )

            cost1 = _solution_total_cost(stage1, vehicle_config, params)
            cost2 = _solution_total_cost(stage2, vehicle_config, params)
            if cost1 is not None and cost2 is not None:
                total_solve_time = round(
                    float(stage1.get("solve_time_seconds", 0) or 0)
                    + float(stage2.get("solve_time_seconds", 0) or 0),
                    2,
                )
                if cost2 < cost1 - 1e-6:
                    stage2["solve_time_seconds"] = total_solve_time
                    best_solution = stage2
                    logger.info(
                        "载重感知二次优化生效: 总成本 %.2f -> %.2f", cost1, cost2
                    )
                else:
                    stage1["solve_time_seconds"] = total_solve_time
                    logger.info(
                        "载重感知二次优化未改进: %.2f vs %.2f", cost2, cost1
                    )

    fallback_solution = best_solution
    candidate_entries: List[
        Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]
    ] = [(best_solution, vehicle_config)]

    if try_fleet_reduction and use_alns:
        fleet_candidates = _try_fleet_reduction(
            best_solution,
            customers_df,
            vehicle_config,
            time_penalty_per_min,
            fuel_price,
            carbon_price,
            time_limit,
            params,
            stage_fuel_price=stage_fuel_price,
        )
        stage_time = float(best_solution.get("solve_time_seconds", 0) or 0)
        if fleet_candidates:
            candidate_entries = []
        for fleet_solution, fleet_config, fleet_cost in fleet_candidates:
            fleet_solution["solve_time_seconds"] = round(
                stage_time
                + float(fleet_solution.get("solve_time_seconds", 0) or 0),
                2,
            )
            candidate_entries.append((fleet_solution, fleet_config))
            logger.info("车队缩减候选入列: 成本 %.2f", fleet_cost)

    if use_alns:
        try:
            run_seeds: Tuple[int, ...] = (42,)
            if len(customers_df) - 1 >= 20:
                per_seed_time = (
                    60.0 if time_limit <= 60 else min(90.0, float(time_limit))
                )
                alns_time = per_seed_time
                peak_start = peak_avoidance_start_minute()
                run_seeds = (
                    42, 47, 49, 60, 62, 70, 71, 91, 92,
                    47, 62, 63, 75, 89, 91, 92,
                )
                seed_overrides: Optional[
                    Sequence[Optional[Dict[str, Any]]]
                ] = tuple(
                    [None] * 9
                    + [{"alns_base_start_minute": peak_start}] * 7
                )
                priority_runs: Optional[
                    Sequence[Tuple[int, Optional[Dict[str, Any]]]]
                ] = (
                    (60, {"alns_base_start_minute": peak_start}),
                    (
                        59,
                        {
                            "alns_base_start_minute": peak_start,
                            "alns_temperature_ratio": 0.018,
                        },
                    ),
                )
            else:
                alns_time = max(2.0, min(8.0, time_limit / 4.0))
                seed_overrides = None
                priority_runs = None
            if len(customers_df) - 1 >= 20:
                customer_count = max(1, len(customers_df) - 1)
                params["alns_iteration_limit"] = max(
                    2000, min(5000, 200000 // customer_count)
                )
                reintensify_params = dict(params)
                reintensify_params.pop("alns_iteration_limit", None)
            before_cost = _solution_total_cost(
                fallback_solution, vehicle_config, params
            )
            best_solution, active_config = _run_alns_portfolio(
                candidate_entries,
                params,
                alns_time,
                seed=42,
                recombine=False,
                recombine_time=0.0,
                seeds=run_seeds,
                seed_params=seed_overrides,
                priority_runs=priority_runs,
                cross_recombine=len(customers_df) - 1 >= 20,
                cross_recombine_time=5.0,
            )
            after_cost = _solution_total_cost(
                best_solution, active_config, params
            )
            if not _solution_fits_fleet(best_solution, active_config):
                logger.warning(
                    "ALNS 候选超出车队数量约束，回退首版解"
                )
                best_solution = fallback_solution
                active_config = vehicle_config
                after_cost = _solution_total_cost(
                    fallback_solution, vehicle_config, params
                )
            if len(customers_df) - 1 >= 20:
                try:
                    polished = _two_opt_star_polish(
                        best_solution,
                        active_config,
                        params,
                        15.0,
                        include_segment=True,
                        include_pairwise=True,
                    )
                    if polished is not None:
                        polished_cost = _solution_total_cost(
                            polished, active_config, params
                        )
                        if polished_cost is not None and (
                            after_cost is None
                            or polished_cost < after_cost - 1e-6
                        ):
                            logger.info(
                                "2-opt* 后处理生效: %.2f -> %.2f",
                                after_cost if after_cost is not None else -1.0,
                                polished_cost,
                            )
                            best_solution = polished
                            after_cost = polished_cost
                except Exception as e:
                    logger.warning(
                        "2-opt* 后处理失败: %s", str(e)[:200]
                    )

            if len(customers_df) - 1 >= 20:
                try:
                    from optimization.alns import (
                        improve_solution_with_alns as _reintensify,
                    )

                    refinements: List[Tuple[str, Dict[str, Any]]] = [
                        (best_solution, active_config)
                    ]
                    reintensified = _reintensify(
                        best_solution,
                        active_config,
                        reintensify_params,
                        time_limit=30.0,
                        seed=203,
                    )
                    refinements.append((reintensified, active_config))
                    for candidate, candidate_config in refinements:
                        candidate_cost = _solution_total_cost(
                            candidate, candidate_config, params
                        )
                        if candidate_cost is not None and (
                            after_cost is None
                            or candidate_cost < after_cost - 1e-6
                        ):
                            logger.info(
                                "最终重强化生效: %.2f -> %.2f",
                                after_cost if after_cost is not None else -1.0,
                                candidate_cost,
                            )
                            best_solution = candidate
                            after_cost = candidate_cost
                except Exception as e:
                    logger.warning(
                        "最终重强化失败: %s", str(e)[:200]
                    )
            result_cost = after_cost
            fallback_cost = _solution_total_cost(
                fallback_solution, vehicle_config, params
            )
            if fallback_cost is not None and (
                after_cost is None or fallback_cost < after_cost - 1e-6
            ):
                best_solution = fallback_solution
                active_config = vehicle_config
                after_cost = fallback_cost
                logger.info(
                    "ALNS 结果不如原解，回退: 候选 %.2f vs 原始 %.2f",
                    result_cost if result_cost is not None else -1.0,
                    fallback_cost,
                )
            logger.info(
                "ALNS 组合优化: 基准 %.2f -> 最终 %s",
                before_cost if before_cost is not None else -1.0,
                f"{after_cost:.2f}" if after_cost is not None else "N/A",
            )
        except Exception as e:
            logger.warning(
                "ALNS 后优化失败（保留原解）: %s",
                str(e)[:200] if e else "未知错误",
            )

    if not _solution_fits_fleet(best_solution, vehicle_config):
        logger.warning(
            "最终解超出车队数量约束，回退首版解"
        )
        best_solution = fallback_solution
    return best_solution


def solve_with_multiple_strategies(
    customers_df: pd.DataFrame,
    vehicle_config: Dict[str, Dict[str, Any]],
    time_penalty_per_min: float = 10.0,
    time_limit: int = 30,
    cost_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    使用多种策略求解，返回最优解（优化版：复用求解器实例）。

    尝试多种初始解策略和元启发式算法组合，
    按完整五维成本选择最优结果返回。

    Args:
        customers_df: 客户数据框
        vehicle_config: 车型配置
        time_penalty_per_min: 迟到惩罚（元/分钟）
        time_limit: 总时间限制
        cost_params: 成本参数（油价、碳价、时薪、迟到罚金等）

    Returns:
        最优求解结果
    """
    strategies = _get_default_strategies()
    params = {**DEFAULT_PARAMS, **(cost_params or {})}
    if cost_params and "late_penalty_per_min" in cost_params:
        time_penalty_per_min = float(cost_params["late_penalty_per_min"])
    fuel_price = float(params.get("fuel_price", DEFAULT_PARAMS["fuel_price"]))
    carbon_price = float(params.get("carbon_price", DEFAULT_PARAMS["carbon_price"]))
    stage_fuel_price = float(
        params.get("stage_fuel_price", fuel_price)
    )

    # 创建单一求解器实例（复用距离矩阵等）
    solver = GreenVRPSolver(
        customers_df=customers_df,
        vehicle_config=vehicle_config,
        time_penalty_per_min=time_penalty_per_min,
        search_time_limit=time_limit,
        fuel_price=stage_fuel_price,
        carbon_price=carbon_price,
    )

    # 每个策略分配的时间
    strategy_time = max(5, time_limit // len(strategies))

    results = []
    for first_solution, metaheuristic in strategies:
        result = solver.solve_with_params(
            first_solution_strategy=first_solution,
            metaheuristic=metaheuristic,
            time_limit=strategy_time,
        )
        results.append(result)

    best_solution = _select_stage_with_probe(
        results,
        vehicle_config,
        params,
        customer_count=len(customers_df) - 1,
    )
    if best_solution is None:
        # 所有策略都失败，返回最后一次尝试的结果
        return results[-1] if results else _create_empty_solution()

    # 2-opt 后处理：消除路线交叉，缩短总距离
    try:
        post_process = _get_route_optimizer()
        best_solution = post_process(best_solution, vehicle_config)
    except Exception as e:
        logger.warning("2-opt 后处理失败（不影响原始解）: %s", str(e)[:200] if e else "未知错误")

    # 第二阶段：按首轮每车平均载重率重建目标并二次求解
    best_solution = refine_solution_with_load_ratios(
        best_solution,
        customers_df,
        vehicle_config,
        time_penalty_per_min=time_penalty_per_min,
        fuel_price=fuel_price,
        carbon_price=carbon_price,
        time_limit=time_limit,
        cost_params=params,
        stage_fuel_price=stage_fuel_price,
    )

    return best_solution


def _create_empty_solution(
    vehicle_config: Optional[Dict[str, Dict[str, Any]]] = None,
    status: str = "NO_SOLUTION_FOUND",
) -> Dict[str, Any]:
    """创建空的求解结果（用于策略全部失败时的降级返回）。"""
    vehicles_used = {}
    if vehicle_config:
        vehicles_used = {v_type: 0 for v_type in vehicle_config}
    return {
        "routes": [],
        "total_distance": 0,
        "vehicles_used": vehicles_used,
        "total_late_minutes": 0,
        "solution_status": status,
        "solve_time_seconds": 0,
    }


def _solve_single_strategy(
    customers_df: pd.DataFrame,
    vehicle_config: Dict[str, Dict[str, Any]],
    time_penalty_per_min: float,
    time_limit: int,
    first_solution_strategy: int,
    metaheuristic: int,
    fuel_price: float,
    carbon_price: float,
    stage_fuel_price: Optional[float] = None,
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
            fuel_price=(
                stage_fuel_price
                if stage_fuel_price is not None
                else fuel_price
            ),
            carbon_price=carbon_price,
        )
        return solver.solve_with_params(
            first_solution_strategy=first_solution_strategy,
            metaheuristic=metaheuristic,
            time_limit=time_limit,
        )
    except Exception as e:
        logger.warning("策略求解失败: %s", str(e)[:200] if e else "未知错误")
        return {
            "routes": [],
            "total_distance": 0,
            "vehicles_used": {v_type: 0 for v_type in vehicle_config},
            "total_late_minutes": 0,
            "solution_status": "ERROR",
            "solve_time_seconds": 0,
        }


def _submit_and_collect_strategies(
    customers_df: pd.DataFrame,
    vehicle_config: Dict[str, Dict[str, Any]],
    time_penalty_per_min: float,
    strategy_time: int,
    strategies: List[Tuple[int, int]],
    max_workers: int,
    fuel_price: float,
    carbon_price: float,
    stage_fuel_price: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    提交策略到进程池并收集所有结果（带超时和取消机制）。

    修复 v1：使用 as_completed 收集所有策略结果，而非仅第一个完成者。
    修复 v2：正确引用 CancelledError。

    Args:
        customers_df: 客户数据
        vehicle_config: 车型配置
        time_penalty_per_min: 迟到惩罚
        strategy_time: 每个策略求解时间
        strategies: 策略列表
        max_workers: 最大进程数

    Returns:
        成功的求解结果列表
    """
    from concurrent.futures import CancelledError

    results: List[Dict[str, Any]] = []

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
                fuel_price,
                carbon_price,
                stage_fuel_price,
            ): (first_solution, metaheuristic)
            for first_solution, metaheuristic in strategies
        }

        # 使用 as_completed 收集所有策略结果
        # 每个策略额外给 30 秒宽限时间（用于进程启动、数据序列化）
        per_strategy_timeout = strategy_time + 30
        completed_count = 0
        for future in as_completed(futures.keys(), timeout=per_strategy_timeout):
            completed_count += 1
            try:
                result = future.result(timeout=5)
                if result["solution_status"] == "SUCCESS":
                    results.append(result)
            except TimeoutError:
                logger.warning("策略结果获取超时")
            except CancelledError:
                continue
            except Exception as e:
                logger.warning("策略执行失败: %s", str(e)[:200] if e else "未知错误")

        # 取消尚未完成的任务
        remaining = len(futures) - completed_count
        if remaining > 0:
            logger.info("正在取消 %d 个超时策略", remaining)
        for future in futures:
            if not future.done():
                future.cancel()

    return results


def solve_with_multiple_strategies_parallel(
    customers_df: pd.DataFrame,
    vehicle_config: Dict[str, Dict[str, Any]],
    time_penalty_per_min: float = 10.0,
    time_limit: int = 30,
    max_workers: Optional[int] = None,
    cost_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    使用多种策略并行求解，返回最优解。

    利用多核CPU并行执行不同策略，显著缩短求解时间。

    Args:
        customers_df: 客户数据框
        vehicle_config: 车型配置
        time_penalty_per_min: 迟到惩罚（元/分钟）
        time_limit: 每个策略的时间限制
        max_workers: 最大并行工作进程数，None则自动检测
        cost_params: 成本参数（油价、碳价、时薪、迟到罚金等）

    Returns:
        最优求解结果

    Note:
        由于Python GIL，使用ProcessPoolExecutor实现真正的并行。
        进程间通信有一定开销，小规模问题可能不如串行版本快。
    """
    strategies = _get_default_strategies()
    params = {**DEFAULT_PARAMS, **(cost_params or {})}
    if cost_params and "late_penalty_per_min" in cost_params:
        time_penalty_per_min = float(cost_params["late_penalty_per_min"])
    fuel_price = float(params.get("fuel_price", DEFAULT_PARAMS["fuel_price"]))
    carbon_price = float(params.get("carbon_price", DEFAULT_PARAMS["carbon_price"]))
    stage_fuel_price = float(
        params.get("stage_fuel_price", fuel_price)
    )

    # 每个策略分配的时间
    strategy_time = max(5, time_limit)

    # 确定工作进程数
    if max_workers is None:
        max_workers = min(len(strategies), multiprocessing.cpu_count())

    start_time = time.time()

    try:
        results = _submit_and_collect_strategies(
            customers_df, vehicle_config, time_penalty_per_min,
            strategy_time, strategies, max_workers,
            fuel_price, carbon_price, stage_fuel_price,
        )
    except Exception as e:
        logger.error("并行执行失败，回退到串行模式: %s", str(e)[:200] if e else "未知错误")
        return solve_with_multiple_strategies(
            customers_df=customers_df,
            vehicle_config=vehicle_config,
            time_penalty_per_min=time_penalty_per_min,
            time_limit=time_limit,
            cost_params=cost_params,
        )

    total_time = time.time() - start_time

    if not results:
        return {
            "routes": [],
            "total_distance": 0,
            "vehicles_used": {v_type: 0 for v_type in vehicle_config},
            "total_late_minutes": 0,
            "solution_status": "NO_SOLUTION_FOUND",
            "solve_time_seconds": round(total_time, 2),
        }

    stage_candidates: List[Dict[str, Any]] = []
    pre_best = _select_best_solution(results, vehicle_config, params)
    ranked_stages = _rank_stages_with_probe(
        results,
        vehicle_config,
        params,
        customer_count=len(customers_df) - 1,
    )
    probe_candidates = (
        [ranked_stages[0][1]] if ranked_stages else []
    )
    stage_signatures = set()
    for candidate in (pre_best, *probe_candidates):
        if candidate is None:
            continue
        if any(candidate is existing for existing in stage_candidates):
            continue
        signature = tuple(
            tuple(
                int(stop["customer_id"])
                for stop in route.get("stops", [])
                if stop.get("customer_id") not in (0, None)
            )
            for route in candidate.get("routes", [])
        )
        if signature in stage_signatures:
            continue
        stage_signatures.add(signature)
        stage_candidates.append(copy.deepcopy(candidate))
    if not stage_candidates:
        return results[0]

    best_solution: Optional[Dict[str, Any]] = None
    best_cost = float("inf")
    for stage_candidate in stage_candidates:
        # 与串行路径保持一致：对最优解执行 2-opt / relocate / exchange 后处理
        try:
            post_process = _get_route_optimizer()
            stage_candidate = post_process(stage_candidate, vehicle_config)
        except Exception as e:
            logger.warning(
                "2-opt 后处理失败（不影响原始解）: %s",
                str(e)[:200] if e else "未知错误",
            )
        refined = refine_solution_with_load_ratios(
            stage_candidate,
            customers_df,
            vehicle_config,
            time_penalty_per_min=time_penalty_per_min,
            fuel_price=fuel_price,
            carbon_price=carbon_price,
            time_limit=time_limit,
            cost_params=params,
            stage_fuel_price=stage_fuel_price,
        )
        refined_cost = _solution_total_cost(
            refined, vehicle_config, params
        )
        if refined_cost is not None and refined_cost < best_cost:
            best_cost = refined_cost
            best_solution = refined

    if best_solution is None:
        best_solution = stage_candidates[0]
    if len(customers_df) - 1 >= 20:
        try:
            pair_polished = _cpsat_pair_polish(
                best_solution, vehicle_config, params, 8.0
            )
            if pair_polished is not None:
                pair_cost = _solution_total_cost(
                    pair_polished, vehicle_config, params
                )
                if (
                    pair_cost is not None
                    and pair_cost < best_cost - 1e-6
                    and _solution_fits_fleet(pair_polished, vehicle_config)
                ):
                    logger.info(
                        "CP-SAT 配对后处理生效: %.2f -> %.2f",
                        best_cost,
                        pair_cost,
                    )
                    best_solution = pair_polished
                    best_cost = pair_cost
        except Exception as e:
            logger.warning(
                "CP-SAT 配对后处理失败: %s", str(e)[:200]
            )
    best_solution["solve_time_seconds"] = round(time.time() - start_time, 2)
    return best_solution
