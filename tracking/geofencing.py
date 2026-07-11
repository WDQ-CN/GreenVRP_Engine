"""
电子围栏模块

实现圆形围栏和区域检测功能。
"""

import math
from typing import List, Optional, Tuple


class Geofence:
    """
    电子围栏（圆形区域）。

    检测车辆位置是否在指定区域内。
    """

    def __init__(self, center_lat: float, center_lon: float, radius_km: float, name: str = ""):
        """
        初始化圆形围栏。

        Args:
            center_lat: 中心纬度
            center_lon: 中心经度
            radius_km: 半径（公里）
            name: 围栏名称
        """
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.radius_km = radius_km
        self.name = name

    def contains(self, lat: float, lon: float) -> bool:
        """判断坐标点是否在围栏内。"""
        distance = self._haversine(self.center_lat, self.center_lon, lat, lon)
        return distance <= self.radius_km

    def distance_to_center(self, lat: float, lon: float) -> float:
        """计算到围栏中心的距离（公里）。"""
        return self._haversine(self.center_lat, self.center_lon, lat, lon)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "center_lat": self.center_lat,
            "center_lon": self.center_lon,
            "radius_km": self.radius_km,
        }

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine 距离计算。"""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def create_depot_geofence(depot_lat: float, depot_lon: float, radius_km: float = 0.5) -> Geofence:
    """创建仓库围栏（用于车辆进出场检测）。"""
    return Geofence(depot_lat, depot_lon, radius_km, name="仓库区域")


def create_customer_geofence(lat: float, lon: float, radius_km: float = 0.1) -> Geofence:
    """创建客户点围栏（用于到达/离开检测）。"""
    return Geofence(lat, lon, radius_km, name="客户点")
