"""
企业简约风格前端组件模块
"""

from .chart_view import (
    create_carbon_emission_chart,
    create_cost_breakdown_chart,
    create_cost_comparison_chart,
    create_efficiency_indicators,
    create_performance_comparison_chart,
    create_time_analysis_chart,
    create_vehicle_utilization_chart,
    enterprise_metric_row,
)
from .map_view import create_enterprise_map, display_route_details, display_route_statistics

__all__ = [
    # 地图组件
    "create_enterprise_map",
    "display_route_statistics",
    "display_route_details",
    # 图表组件
    "create_cost_breakdown_chart",
    "create_cost_comparison_chart",
    "create_performance_comparison_chart",
    "create_carbon_emission_chart",
    "create_vehicle_utilization_chart",
    "create_time_analysis_chart",
    "create_efficiency_indicators",
    "enterprise_metric_row",
]
