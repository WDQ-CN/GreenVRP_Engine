"""
tracking — 车辆追踪模块（最小可行版本）

提供实时位置追踪、GPS 模拟、电子围栏和 ETA 预估功能。
"""

from .eta_calculator import calculate_eta
from .geofencing import Geofence
from .gps_simulator import GPSSimulator, SimulationConfig
from .position_tracker import PositionTracker, VehicleStatus

__all__ = [
    "PositionTracker",
    "VehicleStatus",
    "GPSSimulator",
    "SimulationConfig",
    "Geofence",
    "calculate_eta",
]
