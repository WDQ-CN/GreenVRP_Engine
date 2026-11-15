"""
高级优化模块

提供多目标优化、动态需求响应、碳感知路由、2-opt 后处理等高级优化功能。
"""

from .alns import improve_solution_with_alns
from .carbon_aware import (
    CarbonAwareOptimizer,
    CarbonEfficiencyReport,
)
from .dynamic import (
    DynamicEvent,
    DynamicReoptimizer,
    ReoptimizationResult,
)
from .multi_objective import (
    MultiObjectiveOptimizer,
    ObjectiveWeights,
    ParetoFrontResult,
)
from .route_optimize import (
    exchange_between_routes,
    optimize_single_route,
    post_process_solution,
    relocate_between_routes,
    two_opt_swap,
)
from .recombine import recombine_route_pool

__all__ = [
    "MultiObjectiveOptimizer",
    "ObjectiveWeights",
    "ParetoFrontResult",
    "DynamicReoptimizer",
    "ReoptimizationResult",
    "DynamicEvent",
    "CarbonAwareOptimizer",
    "CarbonEfficiencyReport",
    "two_opt_swap",
    "optimize_single_route",
    "post_process_solution",
    "relocate_between_routes",
    "exchange_between_routes",
    "improve_solution_with_alns",
    "recombine_route_pool",
]
