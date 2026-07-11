"""
单元测试：utils/time.py — 时间工具函数
"""

import pytest
from utils.time import (
    calculate_arrival_time,
    calculate_travel_time,
    is_within_time_window,
    minutes_to_time_str,
    time_str_to_minutes,
)


class TestMinutesToTimeStr:
    def test_zero(self):
        assert minutes_to_time_str(0) == "00:00"

    def test_hours(self):
        assert minutes_to_time_str(480) == "08:00"

    def test_with_minutes(self):
        assert minutes_to_time_str(525) == "08:45"

    def test_rounding(self):
        # int() truncates, so 60.5 → 60 → "01:00"
        assert minutes_to_time_str(60.5) == "01:00"
        assert minutes_to_time_str(60.1) == "01:00"


class TestTimeStrToMinutes:
    def test_basic(self):
        assert time_str_to_minutes("08:00") == 480

    def test_midnight(self):
        assert time_str_to_minutes("00:00") == 0

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            time_str_to_minutes("invalid")

    def test_round_trip(self):
        assert minutes_to_time_str(time_str_to_minutes("14:30")) == "14:30"


class TestCalculateTravelTime:
    def test_basic(self):
        assert calculate_travel_time(40.0, 40.0) == 60.0

    def test_zero_distance(self):
        assert calculate_travel_time(0, 40.0) == 0.0

    def test_zero_speed(self):
        with pytest.raises(ValueError):
            calculate_travel_time(40.0, 0)

    def test_negative_speed(self):
        with pytest.raises(ValueError):
            calculate_travel_time(40.0, -10)


class TestCalculateArrivalTime:
    def test_basic(self):
        assert calculate_arrival_time(480, 40.0, 40.0) == 540  # 480 + 60

    def test_zero_distance(self):
        assert calculate_arrival_time(480, 0, 40.0) == 480


class TestIsWithinTimeWindow:
    def test_within(self):
        ok, late = is_within_time_window(500, 480, 600)
        assert ok is True
        assert late == 0

    def test_early(self):
        ok, late = is_within_time_window(400, 480, 600)
        # 早到被视为在窗内（等待直到时间窗开启）
        assert ok is True
        assert late == 0

    def test_late(self):
        ok, late = is_within_time_window(650, 480, 600)
        assert ok is False
        assert late == 50

    def test_no_window(self):
        ok, late = is_within_time_window(500, None, None)
        assert ok is True
        assert late == 0

    def test_no_earliest(self):
        ok, late = is_within_time_window(500, None, 600)
        assert ok is True
