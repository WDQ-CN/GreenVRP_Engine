"""
地理计算工具函数

提供距离计算、航向计算等地理相关功能。
"""

import math
from typing import List, Optional, Tuple, Union

import numpy as np

from config.constants import EARTH_RADIUS_KM


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    使用 Haversine 公式计算两点间的大圆距离。

    Args:
        lat1: 起点纬度
        lon1: 起点经度
        lat2: 终点纬度
        lon2: 终点经度

    Returns:
        两点间距离（公里）

    Examples:
        >>> haversine_distance(39.9042, 116.4074, 31.2304, 121.4737)
        1068.0  # 北京到上海
    """
    # 转换为弧度
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # 纬度和经度差
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine 公式
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def haversine_distance_vectorized(
    lat1: Union[float, np.ndarray],
    lon1: Union[float, np.ndarray],
    lat2: Union[float, np.ndarray],
    lon2: Union[float, np.ndarray],
) -> Union[float, np.ndarray]:
    """
    向量化版本的 Haversine 距离计算。

    支持广播计算距离矩阵。

    Args:
        lat1: 起点纬度（标量或数组）
        lon1: 起点经度（标量或数组）
        lat2: 终点纬度（标量或数组）
        lon2: 终点经度（标量或数组）

    Returns:
        距离（标量或数组，单位：公里）
    """
    lat1 = np.asarray(lat1, dtype=np.float64)
    lon1 = np.asarray(lon1, dtype=np.float64)
    lat2 = np.asarray(lat2, dtype=np.float64)
    lon2 = np.asarray(lon2, dtype=np.float64)

    # 转换为弧度
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)

    # 纬度和经度差
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine 公式
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def calculate_bearing(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    计算从起点到终点的航向角。

    Args:
        lat1: 起点纬度
        lon1: 起点经度
        lat2: 终点纬度
        lon2: 终点经度

    Returns:
        航向角（度），范围 0-360，0 度为正北

    Examples:
        >>> calculate_bearing(39.90, 116.40, 40.00, 116.40)  # 向北
        0.0
        >>> calculate_bearing(39.90, 116.40, 39.90, 116.50)  # 向东
        90.0
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    x = math.sin(dlon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(
        lat2_rad
    ) * math.cos(dlon)

    bearing = math.atan2(x, y)
    bearing_deg = math.degrees(bearing)

    # 转换为 0-360 范围
    return (bearing_deg + 360) % 360


def destination_point(
    lat: float,
    lon: float,
    bearing: float,
    distance_km: float,
) -> Tuple[float, float]:
    """
    从起点沿指定航向移动指定距离后的终点坐标。

    Args:
        lat: 起点纬度
        lon: 起点经度
        bearing: 航向角（度）
        distance_km: 距离（公里）

    Returns:
        终点坐标 (纬度, 经度)
    """
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing)

    angular_distance = distance_km / EARTH_RADIUS_KM

    lat2 = math.asin(
        math.sin(lat_rad) * math.cos(angular_distance)
        + math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
    )

    lon2 = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(lat2),
    )

    return math.degrees(lat2), math.degrees(lon2)


def point_in_circle(
    point_lat: float,
    point_lon: float,
    center_lat: float,
    center_lon: float,
    radius_km: float,
) -> bool:
    """
    判断点是否在圆形区域内。

    Args:
        point_lat: 点纬度
        point_lon: 点经度
        center_lat: 圆心纬度
        center_lon: 圆心经度
        radius_km: 半径（公里）

    Returns:
        点是否在圆内
    """
    distance = haversine_distance(point_lat, point_lon, center_lat, center_lon)
    return distance <= radius_km


def point_in_polygon(
    point_lat: float,
    point_lon: float,
    polygon: List[Tuple[float, float]],
) -> bool:
    """
    使用射线法判断点是否在多边形区域内。

    Args:
        point_lat: 点纬度
        point_lon: 点经度
        polygon: 多边形顶点列表 [(lat, lon), ...]

    Returns:
        点是否在多边形内
    """
    n = len(polygon)
    if n < 3:
        return False

    inside = False
    j = n - 1

    for i in range(n):
        lat_i, lon_i = polygon[i]
        lat_j, lon_j = polygon[j]

        # 避免除零错误：跳过水平边
        if lat_i != lat_j:
            if ((lat_i > point_lat) != (lat_j > point_lat)) and (
                point_lon < (lon_j - lon_i) * (point_lat - lat_i) / (lat_j - lat_i) + lon_i
            ):
                inside = not inside

        j = i

    return inside


def segments_intersect(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    lat3: float, lon3: float,
    lat4: float, lon4: float,
) -> bool:
    """
    判断两条线段是否相交（跨立实验，平面近似）。

    适用于城市配送场景的小范围经纬度坐标。
    使用快速排斥 + 跨立实验判断两条线段 (p1-p2) 与 (p3-p4) 是否相交。

    Args:
        lat1, lon1: 第一条线段起点
        lat2, lon2: 第一条线段终点
        lat3, lon3: 第二条线段起点
        lat4, lon4: 第二条线段终点

    Returns:
        两条线段是否相交（端点重合不算相交）

    Examples:
        >>> segments_intersect(0, 0, 2, 2, 0, 2, 2, 0)  # 交叉
        True
        >>> segments_intersect(0, 0, 1, 1, 0, 2, 1, 3)  # 不交叉
        False
    """
    def _cross(o_lat, o_lon, a_lat, a_lon, b_lat, b_lon):
        """计算向量 (oa) × (ob) 的叉积 z 分量。"""
        return (a_lat - o_lat) * (b_lon - o_lon) - (a_lon - o_lon) * (b_lat - o_lat)

    def _on_segment(lat_p, lon_p, lat_q, lon_q, lat_r, lon_r):
        """检查点 r 是否在线段 pq 上（四点共线且坐标在范围内）。"""
        return (
            min(lat_p, lat_q) <= lat_r <= max(lat_p, lat_q)
            and min(lon_p, lon_q) <= lon_r <= max(lon_p, lon_q)
        )

    # 快速排斥：检查包围盒是否相交
    if (
        max(lat1, lat2) < min(lat3, lat4)
        or max(lat3, lat4) < min(lat1, lat2)
        or max(lon1, lon2) < min(lon3, lon4)
        or max(lon3, lon4) < min(lon1, lon2)
    ):
        return False

    # 跨立实验
    d1 = _cross(lat3, lon3, lat4, lon4, lat1, lon1)
    d2 = _cross(lat3, lon3, lat4, lon4, lat2, lon2)
    d3 = _cross(lat1, lon1, lat2, lon2, lat3, lon3)
    d4 = _cross(lat1, lon1, lat2, lon2, lat4, lon4)

    if (d1 * d2 < 0) and (d3 * d4 < 0):
        return True

    # 共线情况：端点重合不算相交
    if d1 == 0 and _on_segment(lat3, lon3, lat4, lon4, lat1, lon1):
        return lat1 != lat3 or lon1 != lon3  # 端点重合不算
    if d2 == 0 and _on_segment(lat3, lon3, lat4, lon4, lat2, lon2):
        return lat2 != lat3 or lon2 != lon3
    if d3 == 0 and _on_segment(lat1, lon1, lat2, lon2, lat3, lon3):
        return lat3 != lat1 or lon3 != lon1
    if d4 == 0 and _on_segment(lat1, lon1, lat2, lon2, lat4, lon4):
        return lat4 != lat1 or lon4 != lon1

    return False


def route_distance_km(
    stops: list,
    lat_key: str = "lat",
    lon_key: str = "lon",
) -> float:
    """
    计算路线总里程（公里）。

    遍历 stops 列表，使用 Haversine 公式累加相邻站点间的距离。

    Args:
        stops: 站点列表，每项为包含 lat/lon 的字典
        lat_key: 纬度字段名
        lon_key: 经度字段名

    Returns:
        路线总距离（公里）

    Examples:
        >>> stops = [{"lat": 0, "lon": 0}, {"lat": 1, "lon": 0}, {"lat": 1, "lon": 1}]
        >>> round(route_distance_km(stops), 2)
        222.39
    """
    if not stops or len(stops) < 2:
        return 0.0

    total = 0.0
    for i in range(len(stops) - 1):
        total += haversine_distance(
            stops[i][lat_key], stops[i][lon_key],
            stops[i + 1][lat_key], stops[i + 1][lon_key],
        )
    return total


def build_distance_matrix(
    lats: List[float],
    lons: List[float],
) -> np.ndarray:
    """
    构建距离矩阵。

    Args:
        lats: 纬度列表
        lons: 经度列表

    Returns:
        距离矩阵（公里），shape=(n, n)
    """
    n = len(lats)
    if n == 0:
        return np.array([]).reshape(0, 0)  # 返回二维空数组

    lats_arr = np.array(lats)
    lons_arr = np.array(lons)

    # 使用广播计算距离矩阵
    lat1 = lats_arr[:, np.newaxis]
    lon1 = lons_arr[:, np.newaxis]
    lat2 = lats_arr[np.newaxis, :]
    lon2 = lons_arr[np.newaxis, :]

    return haversine_distance_vectorized(lat1, lon1, lat2, lon2)
