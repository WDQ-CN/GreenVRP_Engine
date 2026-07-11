"""
GPS 模拟器

基于求解路线模拟 GPS 数据流，用于测试和演示。
"""

import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .position_tracker import PositionTracker, VehicleStatus


@dataclass
class SimulationConfig:
    """GPS 模拟配置。"""
    update_interval: float = 5.0
    simulate_traffic: bool = False
    traffic_delay_probability: float = 0.1
    traffic_delay_minutes: int = 10
    speed_factor: float = 1.0


class GPSSimulator:
    """
    GPS 模拟器。

    沿求解路线模拟车辆行驶，定期发送位置更新。
    """

    def __init__(
        self,
        solution: Dict[str, Any],
        vehicle_config: Dict[str, Any],
        tracker: PositionTracker,
        config: Optional[SimulationConfig] = None,
    ):
        self.solution = solution
        self.vehicle_config = vehicle_config
        self.tracker = tracker
        self.config = config or SimulationConfig()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._vehicle_progress: Dict[int, int] = {}

    def start(self) -> None:
        """启动模拟（后台线程）。"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止模拟。"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._running

    def _run(self) -> None:
        """模拟主循环。"""
        for route in self.solution.get("routes", []):
            v_id = route["vehicle_id"]
            stops = route.get("stops", [])
            if not stops:
                continue

            self._vehicle_progress[v_id] = 0

            for i in range(len(stops) - 1):
                if not self._running:
                    return

                current = stops[i]
                next_stop = stops[i + 1]
                self._vehicle_progress[v_id] = i

                # 模拟行驶到下一站点
                speed = self.vehicle_config.get(
                    route.get("vehicle_type", "4.2m"), {}
                ).get("speed_kmh", 40) * self.config.speed_factor

                distance = self._haversine(
                    current.get("lat", 0), current.get("lon", 0),
                    next_stop.get("lat", 0), next_stop.get("lon", 0),
                )
                travel_time = (distance / speed) * 3600 if speed > 0 else 5

                steps = max(1, int(travel_time / self.config.update_interval))
                for step in range(steps):
                    if not self._running:
                        return
                    fraction = (step + 1) / steps
                    lat = current.get("lat", 0) + (next_stop.get("lat", 0) - current.get("lat", 0)) * fraction
                    lon = current.get("lon", 0) + (next_stop.get("lon", 0) - current.get("lon", 0)) * fraction

                    self.tracker.update_position(
                        vehicle_id=v_id, lat=lat, lon=lon,
                        speed_kmh=speed, heading=self._bearing(
                            current.get("lat", 0), current.get("lon", 0),
                            next_stop.get("lat", 0), next_stop.get("lon", 0),
                        ),
                        status=VehicleStatus.TRAVELING,
                    )
                    time.sleep(self.config.update_interval)

                # 到达站点
                self.tracker.update_position(
                    vehicle_id=v_id,
                    lat=next_stop.get("lat", 0),
                    lon=next_stop.get("lon", 0),
                    speed_kmh=0,
                    status=VehicleStatus.SERVING,
                )
                time.sleep(self.config.update_interval)

            # 路线完成
            self.tracker.update_status(v_id, VehicleStatus.COMPLETED)

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间距离（公里）。"""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算方位角（度）。"""
        dlon = math.radians(lon2 - lon1)
        x = math.sin(dlon) * math.cos(math.radians(lat2))
        y = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
        return (math.degrees(math.atan2(x, y)) + 360) % 360
