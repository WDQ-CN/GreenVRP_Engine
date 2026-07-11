# GreenVRP Engine Core Module
"""
核心算法模块：距离计算、VRPTW求解器、成本核算

性能优化版本 v2：
- 距离矩阵：NumPy 向量化计算，O(1)缓存键
- 求解器：时间矩阵缓存、参数化求解、并行多策略
- 成本核算：向量化计算、车型参数缓存
"""

from config.constants import DIESEL_CO2_FACTOR
from config.vehicles import DEFAULT_VEHICLE_CONFIG
from utils.geo import haversine_distance as haversine

from .cost import (
    DEFAULT_CARBON_PRICE,
    calculate_cost_efficiency_metrics,
    calculate_green_cost,
    calculate_green_cost_batch,
    format_cost_report,
)
from .distance import (
    DistanceMatrixCache,
    build_distance_matrix,
    build_time_matrix,
    build_time_matrix_numpy,
    get_location_array,
    get_location_list,
    haversine_vectorized,
)
from .solver import (
    GreenVRPSolver,
    solve_with_multiple_strategies,
    solve_with_multiple_strategies_parallel,
)

__all__ = [
    # 距离计算
    "haversine",
    "haversine_vectorized",
    "build_distance_matrix",
    "build_time_matrix",
    "build_time_matrix_numpy",
    "get_location_list",
    "get_location_array",
    "DistanceMatrixCache",
    # 求解器
    "GreenVRPSolver",
    "solve_with_multiple_strategies",
    "solve_with_multiple_strategies_parallel",
    "DEFAULT_VEHICLE_CONFIG",
    # 成本核算
    "calculate_green_cost",
    "calculate_green_cost_batch",
    "calculate_cost_efficiency_metrics",
    "format_cost_report",
    # 常量
    "DIESEL_CO2_FACTOR",
    "DEFAULT_CARBON_PRICE",
]
