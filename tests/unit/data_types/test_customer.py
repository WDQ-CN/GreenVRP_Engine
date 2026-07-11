"""
单元测试：data_types/customer.py — 客户数据类型
"""

from data_types.customer import Customer


class TestCustomer:
    def test_create(self):
        c = Customer(id=1, lat=39.9, lon=116.4, demand=50,
                      name="客户A", service_time_min=15,
                      tw_earliest=500, tw_latest=600)
        assert c.id == 1
        assert c.lat == 39.9
        assert c.name == "客户A"
        assert c.demand == 50

    def test_minimal(self):
        c = Customer(id=1, lat=39.9, lon=116.4)
        assert c.demand == 0.0
        assert c.name is None
        assert c.service_time_min == 0.0

    def test_to_dict(self):
        c = Customer(id=1, lat=39.9, lon=116.4, demand=50,
                      name="客户A", service_time_min=15,
                      tw_earliest=500, tw_latest=600)
        d = c.to_dict()
        assert d["id"] == 1
        assert d["lat"] == 39.9
        assert d["name"] == "客户A"

    def test_from_dict(self):
        d = {"id": 1, "lat": 39.9, "lon": 116.4, "demand": 50,
             "name": "客户A", "service_time_min": 15,
             "tw_earliest": 500, "tw_latest": 600}
        c = Customer.from_dict(d)
        assert c.id == 1
        assert c.name == "客户A"

    def test_round_trip(self):
        original = Customer(id=2, lat=40.0, lon=116.5, demand=80,
                             name="客户B", service_time_min=20,
                             tw_earliest=600, tw_latest=800)
        restored = Customer.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.demand == original.demand
