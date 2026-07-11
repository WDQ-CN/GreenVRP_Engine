"""
ETA 预估模块

基于 Haversine 距离和平均车速估计到达时间。
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Optional


def calculate_eta(
    current_lat: float, current_lon: float,
    target_lat: float, target_lon: float,
    speed_kmh: float = 40.0,
) -> tuple:
    """
    计算预计到达时间和剩余距离。

    Args:
        current_lat: 当前位置纬度
        current_lon: 当前位置经度
        target_lat: 目标位置纬度
        target_lon: 目标位置经度
        speed_kmh: 平均速度（公里/小时）

    Returns:
        (eta_timestamp, remaining_minutes, distance_km)
    """
    distance_km = _haversine(current_lat, current_lon, target_lat, target_lon)
    remaining_minutes = (distance_km / speed_kmh) * 60 if speed_kmh > 0 else 0
    eta = datetime.now(timezone.utc) + timedelta(minutes=remaining_minutes)
    return eta, round(remaining_minutes, 1), round(distance_km, 2)


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine 距离计算（公里）。"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
