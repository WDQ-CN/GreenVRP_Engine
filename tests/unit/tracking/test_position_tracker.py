"""
单元测试：tracking/position_tracker.py — 位置追踪
"""

import time

import pytest

from tracking.position_tracker import PositionTracker, VehicleSnapshot, VehicleStatus


class TestPositionTracker:
    def test_init_empty(self):
        tracker = PositionTracker()
        assert len(tracker.get_all_vehicles()) == 0

    def test_init_from_solution(self):
        solution = {
            "routes": [
                {
                    "vehicle_id": 0, "vehicle_type": "4.2m",
                    "stops": [{"lat": 39.9, "lon": 116.4}],
                }
            ]
        }
        tracker = PositionTracker(solution)
        vehicles = tracker.get_all_vehicles()
        assert len(vehicles) == 1
        assert vehicles[0].vehicle_id == 0
        assert vehicles[0].vehicle_type == "4.2m"

    def test_update_position(self):
        tracker = PositionTracker()
        # update_position 会自动创建车辆记录
        tracker.update_position(0, 39.91, 116.41, speed_kmh=40.0, status=VehicleStatus.TRAVELING)
        v = tracker.get_vehicle(0)
        assert v is not None
        assert v.lat == 39.91
        assert v.lon == 116.41
        assert v.speed_kmh == 40.0
        assert v.status == VehicleStatus.TRAVELING

    def test_update_status(self):
        tracker = PositionTracker()
        tracker._vehicles[0] = VehicleSnapshot(
            vehicle_id=0, vehicle_type="4.2m",
            status=VehicleStatus.IDLE, lat=39.9, lon=116.4,
        )
        tracker.update_status(0, VehicleStatus.SERVING)
        assert tracker.get_vehicle(0).status == VehicleStatus.SERVING

    def test_get_active_vehicles(self):
        tracker = PositionTracker()
        v1 = VehicleSnapshot(vehicle_id=0, vehicle_type="4.2m", status=VehicleStatus.TRAVELING, lat=0, lon=0)
        v2 = VehicleSnapshot(vehicle_id=1, vehicle_type="4.2m", status=VehicleStatus.COMPLETED, lat=0, lon=0)
        v3 = VehicleSnapshot(vehicle_id=2, vehicle_type="7.6m", status=VehicleStatus.IDLE, lat=0, lon=0)
        tracker._vehicles = {0: v1, 1: v2, 2: v3}
        active = tracker.get_active_vehicles()
        assert len(active) == 1
        assert active[0].vehicle_id == 0

    def test_get_delayed_vehicles(self):
        tracker = PositionTracker()
        v1 = VehicleSnapshot(vehicle_id=0, vehicle_type="4.2m", status=VehicleStatus.DELAYED, lat=0, lon=0, late_minutes=15)
        v2 = VehicleSnapshot(vehicle_id=1, vehicle_type="4.2m", status=VehicleStatus.COMPLETED, lat=0, lon=0, late_minutes=0)
        tracker._vehicles = {0: v1, 1: v2}
        delayed = tracker.get_delayed_vehicles()
        assert len(delayed) == 1

    def test_export_trajectory_geojson(self):
        tracker = PositionTracker()
        tracker._vehicles[0] = VehicleSnapshot(
            vehicle_id=0, vehicle_type="4.2m",
            status=VehicleStatus.COMPLETED, lat=39.9, lon=116.4,
        )
        tracker._trajectories[0] = [
            {"lat": 39.9, "lon": 116.4, "timestamp": 1000.0, "speed_kmh": 0, "heading": 0, "status": "idle"},
            {"lat": 39.91, "lon": 116.41, "timestamp": 1010.0, "speed_kmh": 40, "heading": 45, "status": "traveling"},
        ]
        geojson = tracker.export_trajectory_geojson(0)
        assert geojson is not None
        assert geojson["type"] == "Feature"
        assert geojson["geometry"]["type"] == "LineString"
        assert len(geojson["geometry"]["coordinates"]) == 2

    def test_export_trajectory_too_few_points(self):
        tracker = PositionTracker()
        tracker._vehicles[0] = VehicleSnapshot(
            vehicle_id=0, vehicle_type="4.2m",
            status=VehicleStatus.IDLE, lat=39.9, lon=116.4,
        )
        tracker._trajectories[0] = [{"lat": 39.9, "lon": 116.4}]
        assert tracker.export_trajectory_geojson(0) is None


class TestVehicleSnapshot:
    def test_to_dict(self):
        vs = VehicleSnapshot(
            vehicle_id=0, vehicle_type="4.2m",
            status=VehicleStatus.TRAVELING, lat=39.9, lon=116.4,
            speed_kmh=40.0, heading=90.0,
        )
        d = vs.to_dict()
        assert d["vehicle_id"] == 0
        assert d["status"] == "traveling"
        assert d["lat"] == 39.9
