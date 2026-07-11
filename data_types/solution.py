"""
求解结果类型定义

定义求解结果相关的数据类型。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .cost import CostResult


@dataclass
class Stop:
    """
    站点数据类。

    Attributes:
        node: 节点ID
        lat: 纬度
        lon: 经度
        arrival_time: 到达时间（分钟）
        service_time: 服务时间（分钟）
        tw_earliest: 时间窗最早时间
        tw_latest: 时间窗最晚时间
        customer_id: 客户ID（仓库为 None）
        demand: 需求量
    """

    node: int
    lat: Optional[float] = None
    lon: Optional[float] = None
    arrival_time: Optional[float] = None
    service_time: float = 0.0
    tw_earliest: Optional[float] = None
    tw_latest: Optional[float] = None
    customer_id: Optional[int] = None
    demand: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        result = {"node": self.node}
        if self.lat is not None:
            result["lat"] = self.lat
        if self.lon is not None:
            result["lon"] = self.lon
        if self.arrival_time is not None:
            result["arrival_time"] = self.arrival_time
        if self.service_time != 0.0:
            result["service_time"] = self.service_time
        if self.tw_earliest is not None:
            result["tw_earliest"] = self.tw_earliest
        if self.tw_latest is not None:
            result["tw_latest"] = self.tw_latest
        if self.customer_id is not None:
            result["customer_id"] = self.customer_id
        if self.demand != 0.0:
            result["demand"] = self.demand
        return result


@dataclass
class Route:
    """
    路线数据类。

    Attributes:
        vehicle_id: 车辆ID
        vehicle_type: 车型名称
        distance_km: 行驶距离（公里）
        capacity: 车辆容量
        total_demand: 总需求量
        stops: 站点列表
    """

    vehicle_id: int
    vehicle_type: str
    distance_km: float = 0.0
    capacity: float = 0.0
    total_demand: float = 0.0
    stops: List[Stop] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "vehicle_id": self.vehicle_id,
            "vehicle_type": self.vehicle_type,
            "distance_km": self.distance_km,
            "capacity": self.capacity,
            "total_demand": self.total_demand,
            "stops": [s.to_dict() for s in self.stops],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Route":
        """从字典创建实例。"""
        stops = []
        for s in data.get("stops", []):
            if isinstance(s, Stop):
                stops.append(s)
            else:
                stops.append(
                    Stop(
                        node=s.get("node", 0),
                        lat=s.get("lat"),
                        lon=s.get("lon"),
                        arrival_time=s.get("arrival_time"),
                        service_time=s.get("service_time", 0.0),
                        tw_earliest=s.get("tw_earliest"),
                        tw_latest=s.get("tw_latest"),
                        customer_id=s.get("customer_id"),
                        demand=s.get("demand", 0.0),
                    )
                )
        return cls(
            vehicle_id=data.get("vehicle_id", 0),
            vehicle_type=data.get("vehicle_type", "4.2m"),
            distance_km=data.get("distance_km", 0.0),
            capacity=data.get("capacity", 0.0),
            total_demand=data.get("total_demand", 0.0),
            stops=stops,
        )


@dataclass
class Solution:
    """
    求解结果数据类。

    Attributes:
        solution_status: 求解状态
        routes: 路线列表
        vehicles_used: 使用的车辆数
        total_distance: 总距离
        total_late_minutes: 总迟到分钟数
        cost_data: 成本数据
    """

    solution_status: str = "UNKNOWN"
    routes: List[Route] = field(default_factory=list)
    vehicles_used: Dict[str, int] = field(default_factory=dict)
    total_distance: float = 0.0
    total_late_minutes: float = 0.0
    cost_data: Optional[CostResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "solution_status": self.solution_status,
            "routes": [r.to_dict() for r in self.routes],
            "vehicles_used": self.vehicles_used,
            "total_distance": self.total_distance,
            "total_late_minutes": self.total_late_minutes,
            "cost_data": self.cost_data.to_dict() if self.cost_data else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Solution":
        """从字典创建实例。"""
        routes = []
        for r in data.get("routes", []):
            if isinstance(r, Route):
                routes.append(r)
            else:
                routes.append(Route.from_dict(r))

        cost_data = data.get("cost_data")
        if cost_data is not None and not isinstance(cost_data, CostResult):
            cost_data = CostResult.from_dict(cost_data)

        return cls(
            solution_status=data.get("solution_status", "UNKNOWN"),
            routes=routes,
            vehicles_used=data.get("vehicles_used", {}),
            total_distance=data.get("total_distance", 0.0),
            total_late_minutes=data.get("total_late_minutes", 0.0),
            cost_data=cost_data,
        )
