"""
车辆位置追踪器

管理车辆实时位置、状态和轨迹记录。
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class VehicleStatus(str, Enum):
    """车辆状态枚举。"""
    IDLE = "idle"
    LOADING = "loading"
    TRAVELING = "traveling"
    SERVING = "serving"
    WAITING = "waiting"
    DELAYED = "delayed"
    COMPLETED = "completed"
    OFFLINE = "offline"


@dataclass
class VehicleSnapshot:
    """车辆状态快照。"""
    vehicle_id: int
    vehicle_type: str
    status: VehicleStatus
    lat: float
    lon: float
    speed_kmh: float = 0.0
    heading: float = 0.0
    timestamp: float = 0.0
    stop_index: int = 0
    late_minutes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "vehicle_type": self.vehicle_type,
            "status": self.status.value,
            "lat": self.lat,
            "lon": self.lon,
            "speed_kmh": self.speed_kmh,
            "heading": self.heading,
            "timestamp": self.timestamp,
            "stop_index": self.stop_index,
            "late_minutes": self.late_minutes,
        }


class PositionTracker:
    """
    车辆位置追踪器。

    管理所有车辆的实时位置、状态和历史轨迹。
    """

    def __init__(self, route_solution: Optional[Dict[str, Any]] = None):
        self._vehicles: Dict[int, VehicleSnapshot] = {}
        self._trajectories: Dict[int, List[Dict[str, Any]]] = {}
        self._route_plan: Dict[int, List[Dict[str, Any]]] = {}

        if route_solution:
            self._init_from_solution(route_solution)

    def _init_from_solution(self, solution: Dict[str, Any]) -> None:
        """从求解结果初始化车辆状态。"""
        for route in solution.get("routes", []):
            v_id = route["vehicle_id"]
            stops = route.get("stops", [])
            depot = stops[0] if stops else {"lat": 39.9, "lon": 116.4}

            self._vehicles[v_id] = VehicleSnapshot(
                vehicle_id=v_id,
                vehicle_type=route.get("vehicle_type", "unknown"),
                status=VehicleStatus.IDLE,
                lat=depot.get("lat", 39.9),
                lon=depot.get("lon", 116.4),
                timestamp=time.time(),
            )
            self._route_plan[v_id] = stops
            self._trajectories[v_id] = []

    def _ensure_vehicle(self, vehicle_id: int) -> None:
        """确保车辆和轨迹记录已初始化。"""
        if vehicle_id not in self._vehicles:
            self._vehicles[vehicle_id] = VehicleSnapshot(
                vehicle_id=vehicle_id, vehicle_type="unknown",
                status=VehicleStatus.IDLE, lat=0, lon=0,
            )
        if vehicle_id not in self._trajectories:
            self._trajectories[vehicle_id] = []

    def update_position(
        self, vehicle_id: int, lat: float, lon: float,
        speed_kmh: float = 0.0, heading: float = 0.0,
        status: Optional[VehicleStatus] = None,
    ) -> None:
        """更新车辆位置。"""
        self._ensure_vehicle(vehicle_id)

        vehicle = self._vehicles[vehicle_id]
        vehicle.lat = lat
        vehicle.lon = lon
        vehicle.speed_kmh = speed_kmh
        vehicle.heading = heading
        vehicle.timestamp = time.time()
        if status:
            vehicle.status = status

        self._trajectories[vehicle_id].append({
            "lat": lat, "lon": lon,
            "timestamp": vehicle.timestamp,
            "speed_kmh": speed_kmh,
            "heading": heading,
            "status": vehicle.status.value,
        })

    def update_status(self, vehicle_id: int, status: VehicleStatus) -> None:
        """更新车辆状态。"""
        if vehicle_id in self._vehicles:
            self._vehicles[vehicle_id].status = status
            self._vehicles[vehicle_id].timestamp = time.time()

    def get_vehicle(self, vehicle_id: int) -> Optional[VehicleSnapshot]:
        """获取指定车辆状态。"""
        return self._vehicles.get(vehicle_id)

    def get_active_vehicles(self) -> List[VehicleSnapshot]:
        """获取活跃车辆（非空闲/已完成/离线）。"""
        active_statuses = {
            VehicleStatus.LOADING, VehicleStatus.TRAVELING,
            VehicleStatus.SERVING, VehicleStatus.WAITING,
            VehicleStatus.DELAYED,
        }
        return [
            v for v in self._vehicles.values()
            if v.status in active_statuses
        ]

    def get_delayed_vehicles(self) -> List[VehicleSnapshot]:
        """获取延误车辆。"""
        return [
            v for v in self._vehicles.values()
            if v.status == VehicleStatus.DELAYED or v.late_minutes > 0
        ]

    def get_all_vehicles(self) -> List[VehicleSnapshot]:
        """获取所有车辆状态。"""
        return list(self._vehicles.values())

    def export_trajectory_geojson(self, vehicle_id: int) -> Optional[Dict[str, Any]]:
        """导出车辆轨迹为 GeoJSON LineString。"""
        points = self._trajectories.get(vehicle_id)
        if not points or len(points) < 2:
            return None

        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[p["lon"], p["lat"]] for p in points],
            },
            "properties": {
                "vehicle_id": vehicle_id,
                "vehicle_type": self._vehicles[vehicle_id].vehicle_type,
                "point_count": len(points),
                "start_time": points[0]["timestamp"],
                "end_time": points[-1]["timestamp"],
            },
        }
