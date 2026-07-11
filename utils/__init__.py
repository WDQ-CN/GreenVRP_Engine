"""
工具函数模块

提供通用的工具函数。
"""

from utils.geo import (
    calculate_bearing,
    destination_point,
    haversine_distance,
    haversine_distance_vectorized,
    point_in_circle,
    point_in_polygon,
)
from utils.time import (
    calculate_travel_time,
    minutes_to_time_str,
    time_str_to_minutes,
)
from utils.validation import (
    validate_customer,
    validate_params,
    validate_vehicle_config,
)

__all__ = [
    # geo
    "haversine_distance",
    "haversine_distance_vectorized",
    "calculate_bearing",
    "destination_point",
    "point_in_circle",
    "point_in_polygon",
    # time
    "minutes_to_time_str",
    "time_str_to_minutes",
    "calculate_travel_time",
    # validation
    "validate_customer",
    "validate_vehicle_config",
    "validate_params",
]
