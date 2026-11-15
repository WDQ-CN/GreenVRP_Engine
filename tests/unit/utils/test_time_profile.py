"""Tests for the time-of-day speed profile."""

import pytest

from utils.time_profile import (
    average_speed_multiplier,
    fuel_speed_factor,
    peak_avoidance_start_minute,
    speed_multiplier,
    travel_time_minutes,
)


def test_speed_multiplier_bands():
    assert speed_multiplier(480) == pytest.approx(0.65)
    assert speed_multiplier(600) == pytest.approx(1.0)
    assert speed_multiplier(1030) == pytest.approx(0.70)
    assert speed_multiplier(400) == pytest.approx(1.15)


def test_peak_travel_is_slower_than_offpeak():
    peak = travel_time_minutes(30.0, 480, 40.0)
    offpeak = travel_time_minutes(30.0, 600, 40.0)
    assert peak == pytest.approx(66.0, abs=0.1)
    assert offpeak == pytest.approx(45.0, abs=0.1)
    assert peak > offpeak


def test_zero_distance_and_cross_band():
    assert travel_time_minutes(0.0, 480, 40.0) == 0.0
    # 30 km starting at 08:00: 26 km in the peak band, then 4 km at daytime speed.
    assert travel_time_minutes(30.0, 480, 40.0) == pytest.approx(66.0, abs=0.1)


def test_average_working_day_factor():
    assert average_speed_multiplier() == pytest.approx(0.935, abs=0.001)


def test_peak_avoidance_start_is_morning_peak_end():
    assert peak_avoidance_start_minute() == 540


def test_fuel_speed_factor_penalises_peaks():
    assert fuel_speed_factor(1.0) == pytest.approx(1.0, abs=1e-9)
    assert fuel_speed_factor(0.65) > 1.0
    assert fuel_speed_factor(1.15) > 1.0
