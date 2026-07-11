"""
单元测试：models/customer.py — Customer ORM 模型 CRUD
"""

import pytest
from sqlalchemy import text

from models.customer import Customer


class TestCustomerCRUD:
    def test_create_customer(self, fresh_db):
        customer = Customer(
            scenario_id=1,
            customer_id=1,
            name="测试客户A",
            lat=39.91,
            lon=116.34,
            demand=50,
            service_time_min=15,
            tw_earliest=480,
            tw_latest=600,
        )
        fresh_db.add(customer)
        fresh_db.commit()

        saved = fresh_db.query(Customer).filter_by(customer_id=1).first()
        assert saved is not None
        assert saved.name == "测试客户A"
        assert saved.demand == 50

    def test_read_customer(self, fresh_db):
        customer = Customer(
            scenario_id=1, customer_id=2, name="客户B",
            lat=39.92, lon=116.35,
        )
        fresh_db.add(customer)
        fresh_db.commit()

        found = fresh_db.query(Customer).filter_by(customer_id=2).first()
        assert found is not None
        assert found.lat == 39.92

    def test_update_customer(self, fresh_db):
        customer = Customer(
            scenario_id=1, customer_id=3, name="客户C",
            lat=39.93, lon=116.36, demand=30,
        )
        fresh_db.add(customer)
        fresh_db.commit()

        customer.demand = 60
        fresh_db.commit()

        updated = fresh_db.query(Customer).filter_by(customer_id=3).first()
        assert updated.demand == 60

    def test_delete_customer(self, fresh_db):
        customer = Customer(
            scenario_id=1, customer_id=4, name="客户D",
            lat=39.94, lon=116.37,
        )
        fresh_db.add(customer)
        fresh_db.commit()

        fresh_db.delete(customer)
        fresh_db.commit()

        deleted = fresh_db.query(Customer).filter_by(customer_id=4).first()
        assert deleted is None

    def test_to_dict(self, fresh_db):
        customer = Customer(
            scenario_id=1, customer_id=5, name="客户E",
            lat=39.95, lon=116.38, demand=80,
            service_time_min=20, tw_earliest=500, tw_latest=700,
        )
        d = customer.to_dict()
        assert d["id"] == 5
        assert d["name"] == "客户E"
        assert d["demand"] == 80
        assert d["tw_earliest"] == 500

    def test_customer_repr(self):
        customer = Customer(
            scenario_id=1, customer_id=6, name="客户F", demand=45,
            lat=39.96, lon=116.39,
        )
        assert "客户F" in repr(customer)
        assert "45" in repr(customer)
