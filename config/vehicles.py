"""
车型配置模块

统一管理车辆配置信息。
"""

from typing import Dict, Optional, TypedDict


class VehicleConfigDict(TypedDict, total=False):
    """车型配置字典类型。"""

    capacity: float
    """载重量（公斤）"""

    fixed_cost: float
    """固定成本（元）"""

    fuel_per_100km: float
    """油耗（升/100公里）"""

    speed_kmh: float
    """平均时速（公里/小时）"""

    count: int
    """可用车辆数"""

    color: str
    """可视化颜色"""


# 默认车型配置
DEFAULT_VEHICLE_CONFIG: Dict[str, VehicleConfigDict] = {
    "4.2m": {
        "capacity": 800,
        "fixed_cost": 200,
        "fuel_per_100km": 12,
        "speed_kmh": 40,
        "count": 3,
        "color": "#1f77b4",
    },
    "7.6m": {
        "capacity": 1500,
        "fixed_cost": 350,
        "fuel_per_100km": 18,
        "speed_kmh": 35,
        "count": 2,
        "color": "#2ca02c",
    },
    "9.6m": {
        "capacity": 2500,
        "fixed_cost": 500,
        "fuel_per_100km": 25,
        "speed_kmh": 30,
        "count": 2,
        "color": "#9467bd",
    },
}


def get_vehicle_config(vehicle_type: str) -> Optional[VehicleConfigDict]:
    """
    获取指定车型的配置。

    Args:
        vehicle_type: 车型名称

    Returns:
        车型配置字典，如果不存在则返回 None
    """
    return DEFAULT_VEHICLE_CONFIG.get(vehicle_type)


def get_vehicle_speed(vehicle_type: str, default: float = 40.0) -> float:
    """
    获取指定车型的速度。

    Args:
        vehicle_type: 车型名称
        default: 默认速度

    Returns:
        车型速度（公里/小时）
    """
    config = get_vehicle_config(vehicle_type)
    if config:
        return config.get("speed_kmh", default)
    return default


def get_vehicle_capacity(vehicle_type: str, default: float = 800.0) -> float:
    """
    获取指定车型的载重量。

    Args:
        vehicle_type: 车型名称
        default: 默认载重量

    Returns:
        车型载重量（公斤）
    """
    config = get_vehicle_config(vehicle_type)
    if config:
        return config.get("capacity", default)
    return default
