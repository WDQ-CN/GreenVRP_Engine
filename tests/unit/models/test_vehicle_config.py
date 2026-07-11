"""
单元测试：models/vehicle_config.py — VehicleConfig ORM 模型
"""

import pytest

from models.vehicle_config import VehicleConfig, get_default_vehicle_configs


class TestVehicleConfigCRUD:
    def test_create_vehicle_config(self, fresh_db):
        vc = VehicleConfig(
            name="4.2m",
            capacity=800,
            fixed_cost=200,
            fuel_per_100km=12,
            speed_kmh=40,
            count=3,
            color="#1f77b4",
        )
        fresh_db.add(vc)
        fresh_db.commit()

        saved = fresh_db.query(VehicleConfig).filter_by(name="4.2m").first()
        assert saved is not None
        assert saved.capacity == 800
        assert saved.count == 3

    def test_read_vehicle_config(self, fresh_db):
        vc = VehicleConfig(name="7.6m", capacity=1500)
        fresh_db.add(vc)
        fresh_db.commit()

        found = fresh_db.query(VehicleConfig).filter_by(name="7.6m").first()
        assert found is not None
        assert found.capacity == 1500

    def test_update_vehicle_config(self, fresh_db):
        vc = VehicleConfig(name="9.6m", capacity=2500, count=2)
        fresh_db.add(vc)
        fresh_db.commit()

        vc.count = 5
        fresh_db.commit()

        updated = fresh_db.query(VehicleConfig).filter_by(name="9.6m").first()
        assert updated.count == 5

    def test_delete_vehicle_config(self, fresh_db):
        vc = VehicleConfig(name="test-vehicle", capacity=1000)
        fresh_db.add(vc)
        fresh_db.commit()

        fresh_db.delete(vc)
        fresh_db.commit()

        deleted = fresh_db.query(VehicleConfig).filter_by(name="test-vehicle").first()
        assert deleted is None

    def test_to_dict(self):
        vc = VehicleConfig(
            name="4.2m", capacity=800, fixed_cost=200,
            fuel_per_100km=12, speed_kmh=40, count=3, color="#1f77b4",
        )
        d = vc.to_dict()
        assert d["capacity"] == 800
        assert d["fixed_cost"] == 200
        assert d["count"] == 3

    def test_get_default_vehicle_configs(self):
        configs = get_default_vehicle_configs()
        assert "4.2m" in configs
        assert "7.6m" in configs
        assert "9.6m" in configs
        assert configs["4.2m"]["capacity"] == 800
        assert configs["7.6m"]["count"] == 2

    def test_vehicle_config_repr(self):
        vc = VehicleConfig(name="4.2m", capacity=800)
        assert "4.2m" in repr(vc)
        assert "800" in repr(vc)
