"""
时间处理工具函数

提供时间转换和计算功能。
"""

from typing import Optional, Tuple


def minutes_to_time_str(minutes: float) -> str:
    """
    将分钟数转换为时间字符串。

    Args:
        minutes: 从午夜开始的分钟数

    Returns:
        时间字符串 (HH:MM 格式)

    Examples:
        >>> minutes_to_time_str(480)
        '08:00'
        >>> minutes_to_time_str(960)
        '16:00'
    """
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"


def time_str_to_minutes(time_str: str) -> int:
    """
    将时间字符串转换为分钟数。

    Args:
        time_str: 时间字符串 (HH:MM 格式)

    Returns:
        从午夜开始的分钟数

    Raises:
        ValueError: 时间格式无效

    Examples:
        >>> time_str_to_minutes('08:00')
        480
        >>> time_str_to_minutes('16:00')
        960
    """
    parts = time_str.split(":")
    if len(parts) != 2:
        raise ValueError(f"无效的时间格式: {time_str}，期望 HH:MM")

    hours = int(parts[0])
    minutes = int(parts[1])

    return hours * 60 + minutes


def calculate_travel_time(
    distance_km: float,
    speed_kmh: float,
) -> float:
    """
    计算行驶时间。

    Args:
        distance_km: 距离（公里）
        speed_kmh: 速度（公里/小时）

    Returns:
        行驶时间（分钟）

    Examples:
        >>> calculate_travel_time(100, 50)
        120.0
    """
    if speed_kmh <= 0:
        raise ValueError("速度必须为正数")

    return (distance_km / speed_kmh) * 60


def calculate_arrival_time(
    departure_time: float,
    distance_km: float,
    speed_kmh: float,
    service_time: float = 0.0,
) -> float:
    """
    计算到达时间。

    Args:
        departure_time: 出发时间（分钟）
        distance_km: 距离（公里）
        speed_kmh: 速度（公里/小时）
        service_time: 服务时间（分钟）

    Returns:
        到达时间（分钟）
    """
    travel_time = calculate_travel_time(distance_km, speed_kmh)
    return departure_time + travel_time + service_time


def is_within_time_window(
    arrival_time: float,
    tw_earliest: Optional[float],
    tw_latest: Optional[float],
) -> Tuple[bool, float]:
    """
    检查到达时间是否在时间窗内。

    Args:
        arrival_time: 到达时间（分钟）
        tw_earliest: 时间窗最早时间
        tw_latest: 时间窗最晚时间

    Returns:
        (是否在时间窗内, 迟到分钟数)
    """
    if tw_latest is None:
        return True, 0.0

    if arrival_time <= tw_latest:
        return True, 0.0
    else:
        return False, arrival_time - tw_latest
