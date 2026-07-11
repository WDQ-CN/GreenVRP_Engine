"""
配置模块

统一管理项目配置和常量。
"""

from config.constants import (
    DEFAULT_PARAMS,
    DIESEL_CO2_FACTOR,
    EARTH_RADIUS_KM,
    VEHICLE_CARBON_BASELINE,
)
from config.settings import Settings, get_settings
from config.vehicles import DEFAULT_VEHICLE_CONFIG, VehicleConfigDict

__all__ = [
    "Settings",
    "get_settings",
    "DEFAULT_VEHICLE_CONFIG",
    "VehicleConfigDict",
    "DIESEL_CO2_FACTOR",
    "VEHICLE_CARBON_BASELINE",
    "EARTH_RADIUS_KM",
    "DEFAULT_PARAMS",
]
