"""
单元测试：models/scenario.py — Scenario ORM 模型 CRUD
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from models.customer import Customer
from models.scenario import Scenario
from models.solution import Solution
from models.vehicle_config import VehicleConfig


class TestScenarioCRUD:
    def test_create_scenario(self, fresh_db):
        scenario = Scenario(name="测试场景A", description="用于测试")
        fresh_db.add(scenario)
        fresh_db.commit()

        saved = fresh_db.query(Scenario).filter_by(name="测试场景A").first()
        assert saved is not None
        assert saved.description == "用于测试"
        assert saved.created_at is not None

    def test_read_scenario(self, fresh_db):
        scenario = Scenario(name="场景B")
        fresh_db.add(scenario)
        fresh_db.commit()

        found = fresh_db.query(Scenario).filter_by(name="场景B").first()
        assert found is not None

    def test_update_scenario(self, fresh_db):
        scenario = Scenario(name="场景C", description="旧描述")
        fresh_db.add(scenario)
        fresh_db.commit()

        scenario.description = "新描述"
        fresh_db.commit()

        updated = fresh_db.query(Scenario).filter_by(name="场景C").first()
        assert updated.description == "新描述"

    def test_delete_scenario(self, fresh_db):
        scenario = Scenario(name="场景D")
        fresh_db.add(scenario)
        fresh_db.commit()

        fresh_db.delete(scenario)
        fresh_db.commit()

        deleted = fresh_db.query(Scenario).filter_by(name="场景D").first()
        assert deleted is None

    def test_cascade_delete_customers(self, fresh_db):
        """验证级联删除：删除场景时自动删除关联客户。"""
        scenario = Scenario(name="级联测试场景")
        fresh_db.add(scenario)
        fresh_db.flush()

        customer = Customer(
            scenario_id=scenario.id, customer_id=1, name="级联客户",
            lat=39.9, lon=116.4,
        )
        fresh_db.add(customer)
        fresh_db.commit()

        fresh_db.delete(scenario)
        fresh_db.commit()

        deleted_customer = fresh_db.query(Customer).filter_by(customer_id=1).first()
        assert deleted_customer is None

    def test_scenario_customer_relationship(self, fresh_db):
        """验证 Scenario→Customer 一对多关系。"""
        scenario = Scenario(name="关系测试")
        fresh_db.add(scenario)
        fresh_db.flush()

        c1 = Customer(scenario_id=scenario.id, customer_id=1, name="关系客户1", lat=39.9, lon=116.4)
        c2 = Customer(scenario_id=scenario.id, customer_id=2, name="关系客户2", lat=39.91, lon=116.41)
        fresh_db.add_all([c1, c2])
        fresh_db.commit()

        fresh_db.refresh(scenario)
        assert len(scenario.customers) == 2

    def test_scenario_solution_relationship(self, fresh_db):
        """验证 Scenario→Solution 一对多关系。"""
        scenario = Scenario(name="方案关系测试")
        fresh_db.add(scenario)
        fresh_db.flush()

        s1 = Solution(scenario_id=scenario.id, job_id="job-001", status="completed")
        s2 = Solution(scenario_id=scenario.id, job_id="job-002", status="pending")
        fresh_db.add_all([s1, s2])
        fresh_db.commit()

        fresh_db.refresh(scenario)
        assert len(scenario.solutions) == 2

    def test_scenario_repr(self):
        scenario = Scenario(name="展示场景", id=42)
        assert "展示场景" in repr(scenario)
        assert "42" in repr(scenario)
