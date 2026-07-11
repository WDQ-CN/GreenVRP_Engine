"""
车辆类型定义

定义车辆配置和状态相关的数据类型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class VehicleStatus(str, Enum):
    """车辆状态枚举。"""

    IDLE = "idle"
    """空闲"""

    LOADING = "loading"
    """装载中"""

    TRAVELING = "traveling"
    """行驶中"""

    SERVING = "serving"
    """服务中"""

    WAITING = "waiting"
    """等待中"""

    DELAYED = "delayed"
    """延误"""

    COMPLETED = "completed"
    """已完成"""

    OFFLINE = "offline"
    """离线"""


@dataclass
class VehicleConfig:
    """
    车辆配置数据类。

    Attributes:
        vehicle_type: 车型名称
        capacity: 载重量（公斤）
        fixed_cost: 固定成本（元）
        fuel_per_100km: 油耗（升/100公里）
        speed_kmh: 平均时速（公里/小时）
        count: 可用车辆数
        color: 可视化颜色
    """

    vehicle_type: str
    capacity: float
    fixed_cost: float
    fuel_per_100km: float
    speed_kmh: float
    count: int = 1
    color: str = "#1f77b4"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "vehicle_type": self.vehicle_type,
            "capacity": self.capacity,
            "fixed_cost": self.fixed_cost,
            "fuel_per_100km": self.fuel_per_100km,
            "speed_kmh": self.speed_kmh,
            "count": self.count,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VehicleConfig":
        """从字典创建实例。"""
        return cls(
            vehicle_type=data.get("vehicle_type", "unknown"),
            capacity=data.get("capacity", 800),
            fixed_cost=data.get("fixed_cost", 200),
            fuel_per_100km=data.get("fuel_per_100km", 12),
            speed_kmh=data.get("speed_kmh", 40),
            count=data.get("count", 1),
            color=data.get("color", "#1f77b4"),
        )


@dataclass
class VehicleState:
    """
    车辆状态数据类。

    Attributes:
        vehicle_id: 车辆ID
        vehicle_type: 车型名称
        status: 当前状态
        current_lat: 当前纬度
        current_lon: 当前经度
        current_stop_index: 当前站点索引
        route_index: 路线索引
        last_update: 最后更新时间
        speed_kmh: 当前速度
        heading: 航向角
        distance_traveled: 已行驶距离
        eta_next_stop: 到达下一站点的预计时间
        late_minutes: 迟到分钟数
        metadata: 元数据
    """

    vehicle_id: int
    vehicle_type: str
    status: VehicleStatus
    current_lat: float
    current_lon: float
    current_stop_index: int
    route_index: int
    last_update: datetime | None = None
    speed_kmh: float = 0.0
    heading: float = 0.0
    distance_traveled: float = 0.0
    eta_next_stop: float | None = None
    late_minutes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "vehicle_id": self.vehicle_id,
            "vehicle_type": self.vehicle_type,
            "status": self.status.value,
            "current_lat": self.current_lat,
            "current_lon": self.current_lon,
            "current_stop_index": self.current_stop_index,
            "route_index": self.route_index,
            "last_update": self.last_update.isoformat()
            if hasattr(self.last_update, "isoformat")
            else str(self.last_update),
            "speed_kmh": self.speed_kmh,
            "heading": self.heading,
            "distance_traveled": self.distance_traveled,
            "eta_next_stop": self.eta_next_stop,
            "late_minutes": self.late_minutes,
            "metadata": self.metadata,
        }
