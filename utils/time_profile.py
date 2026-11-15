"""Time-of-day speed profile for time-dependent green routing.

The profile is deliberately simple and data-driven: a nominal vehicle speed
is multiplied by a time-band factor.  Morning/evening peaks slow vehicles
down and increase fuel consumption per kilometre, following the time-dependent
green VRP literature (Zhou et al., 2019/2025; Zhao et al., 2020).
"""

from __future__ import annotations

from typing import List, Tuple

# (band_start_minute, band_end_minute, speed_multiplier)
SPEED_PROFILE: List[Tuple[int, int, float]] = [
    (0, 420, 1.15),
    (420, 540, 0.65),    # 07:00-09:00 morning peak
    (540, 1020, 1.00),   # 09:00-17:00 daytime
    (1020, 1140, 0.70),  # 17:00-19:00 evening peak
    (1140, 1440, 1.10),
]

PROFILE_DAY_END = 1440
INF_FALLBACK = 1e9


def speed_multiplier(minute: float) -> float:
    """Return the speed multiplier at a given minute of day."""
    minute = minute % PROFILE_DAY_END
    if minute < 420:
        return 1.15
    if minute < 540:
        return 0.65
    if minute < 1020:
        return 1.00
    if minute < 1140:
        return 0.70
    return 1.10


def next_band_boundary(minute: float) -> int:
    """Return the end of the band containing `minute`."""
    minute = minute % PROFILE_DAY_END
    if minute < 420:
        return 420
    if minute < 540:
        return 540
    if minute < 1020:
        return 1020
    if minute < 1140:
        return 1140
    return PROFILE_DAY_END


def travel_time_minutes(
    distance_km: float,
    departure_minute: float,
    base_speed_kmh: float,
) -> float:
    """Travel time for a leg that may cross one or more speed bands."""
    if distance_km <= 0 or base_speed_kmh <= 0:
        return 0.0

    remaining_km = distance_km
    clock = float(departure_minute)
    started = clock

    for _ in range(64):
        multiplier = speed_multiplier(clock)
        speed_kmh = base_speed_kmh * multiplier
        if speed_kmh <= 0:
            return INF_FALLBACK
        boundary = next_band_boundary(clock)
        minutes_in_band = boundary - clock
        if minutes_in_band <= 0:
            return (clock - started) + remaining_km / speed_kmh * 60.0

        capacity_km = speed_kmh * minutes_in_band / 60.0
        if capacity_km >= remaining_km:
            return (clock - started) + remaining_km / speed_kmh * 60.0

        remaining_km -= capacity_km
        clock = boundary

    return (clock - started) + remaining_km / max(base_speed_kmh * speed_multiplier(clock), 1e-9) * 60.0


def average_speed_multiplier(
    start_minute: float = 480,
    end_minute: float = 1080,
) -> float:
    """Duration-weighted average speed multiplier over a working period."""
    total = 0.0
    duration = 0.0
    for band_start, band_end, multiplier in SPEED_PROFILE:
        overlap_start = max(start_minute, band_start)
        overlap_end = min(end_minute, band_end)
        if overlap_end > overlap_start:
            span = overlap_end - overlap_start
            total += span * multiplier
            duration += span
    return total / duration if duration > 0 else 1.0


def peak_avoidance_start_minute() -> int:
    """Return the first morning departure time after congestion clears."""
    for _start, end, multiplier in SPEED_PROFILE:
        if multiplier < 1.0:
            return int(end)
    return int(SPEED_PROFILE[0][0])


def fuel_speed_factor(multiplier: float) -> float:
    """Fuel-per-km multiplier for a speed band.

    Calibrated so the nominal speed has factor 1.0; low speeds are penalised
    for stop-and-go/idling and high speeds for aerodynamic drag.
    """
    ratio = multiplier
    if ratio < 0.3:
        ratio = 0.3
    elif ratio > 1.5:
        ratio = 1.5
    return 0.35 / ratio + 0.45 + 0.20 * ratio * ratio
