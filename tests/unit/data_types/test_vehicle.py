"""
单元测试：data_types/vehicle.py — 车辆数据类型
"""

from datetime import datetime, timezone

from data_types.vehicle import VehicleConfig, VehicleState, VehicleStatus


class TestVehicleConfig:
    def test_create(self):
        v = VehicleConfig(vehicle_type="4.2m", capacity=800, fixed_cost=200,
                           fuel_per_100km=12, speed_kmh=40, count=3)
        assert v.vehicle_type == "4.2m"
        assert v.capacity == 800
        assert v.count == 3

    def test_default_color(self):
        v = VehicleConfig(vehicle_type="4.2m", capacity=800, fixed_cost=200,
                           fuel_per_100km=12, speed_kmh=40)
        assert v.color == "#1f77b4"


class TestVehicleStatus:
    def test_enum_values(self):
        assert VehicleStatus.IDLE.value == "idle"
        assert VehicleStatus.LOADING.value == "loading"
        assert VehicleStatus.TRAVELING.value == "traveling"
        assert VehicleStatus.COMPLETED.value == "completed"


class TestVehicleState:
    def test_create(self):
        vs = VehicleState(
            vehicle_id=1, vehicle_type="4.2m", status=VehicleStatus.IDLE,
            current_lat=39.9, current_lon=116.4,
            current_stop_index=0, route_index=0,
        )
        assert vs.vehicle_id == 1
        assert vs.status == VehicleStatus.IDLE
        assert vs.current_lat == 39.9

    def test_with_timestamp(self):
        now = datetime.now(timezone.utc)
        vs = VehicleState(
            vehicle_id=1, vehicle_type="4.2m", status=VehicleStatus.TRAVELING,
            current_lat=39.9, current_lon=116.4,
            current_stop_index=1, route_index=0,
            last_update=now, speed_kmh=40.0,
        )
        assert vs.last_update == now
        assert vs.speed_kmh == 40.0
