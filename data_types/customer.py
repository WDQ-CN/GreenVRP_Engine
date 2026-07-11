"""
客户类型定义

定义客户相关的数据类型。
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Customer:
    """
    客户数据类。

    Attributes:
        id: 客户唯一标识
        lat: 纬度
        lon: 经度
        demand: 需求量（公斤）
        name: 客户名称
        service_time_min: 服务时间（分钟）
        tw_earliest: 时间窗最早时间（分钟，从午夜开始）
        tw_latest: 时间窗最晚时间（分钟，从午夜开始）
    """

    id: int
    lat: float
    lon: float
    demand: int = 0
    name: Optional[str] = None
    service_time_min: int = 0
    tw_earliest: Optional[int] = None
    tw_latest: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        result = {
            "id": self.id,
            "lat": self.lat,
            "lon": self.lon,
            "demand": self.demand,
        }
        if self.name is not None:
            result["name"] = self.name
        if self.service_time_min != 0.0:
            result["service_time_min"] = self.service_time_min
        if self.tw_earliest is not None:
            result["tw_earliest"] = self.tw_earliest
        if self.tw_latest is not None:
            result["tw_latest"] = self.tw_latest
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Customer":
        """从字典创建实例。"""
        return cls(
            id=data["id"],
            lat=data["lat"],
            lon=data["lon"],
            demand=int(data.get("demand", 0)),
            name=data.get("name"),
            service_time_min=data.get("service_time_min", 0.0),
            tw_earliest=data.get("tw_earliest"),
            tw_latest=data.get("tw_latest"),
        )


# 客户列表类型别名
CustomerList = List[Customer]


def dict_to_customers(data: List[Dict[str, Any]]) -> CustomerList:
    """
    将字典列表转换为 Customer 列表。

    Args:
        data: 字典列表

    Returns:
        Customer 实例列表
    """
    return [Customer.from_dict(item) for item in data]


def customers_to_dict(customers: CustomerList) -> List[Dict[str, Any]]:
    """
    将 Customer 列表转换为字典列表。

    Args:
        customers: Customer 实例列表

    Returns:
        字典列表
    """
    return [c.to_dict() for c in customers]
