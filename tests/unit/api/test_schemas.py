"""
单元测试：api/schemas/request.py
"""

import pytest
from pydantic import ValidationError

from api.schemas.request import (
    CustomerData,
    ScenarioCreate,
    ScenarioUpdate,
    SolveRequest,
    SolverParams,
    VehicleConfigItem,
)


# =========================================================================
# CustomerData
# =========================================================================

class TestCustomerData:
    def test_valid_customer(self):
        c = CustomerData(
            id=1, name="客户A", lat=39.9, lon=116.4,
            demand=50, service_time_min=15,
            tw_earliest=500, tw_latest=600,
        )
        assert c.id == 1
        assert c.name == "客户A"
        assert c.lat == 39.9
        assert c.lon == 116.4
        assert c.demand == 50
        assert c.service_time_min == 15
        assert c.tw_earliest == 500
        assert c.tw_latest == 600

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("lat", 95.0), ("lat", -91.0),
            ("lon", 181.0), ("lon", -181.0),
            ("demand", -1), ("service_time_min", -1),
            ("id", -1), ("tw_earliest", -1), ("tw_earliest", 1441),
            ("tw_latest", -1), ("tw_latest", 1441),
        ],
    )
    def test_out_of_range(self, field, value):
        kwargs = dict(id=1, name="客户A", lat=39.9, lon=116.4,
                      demand=50, service_time_min=15,
                      tw_earliest=500, tw_latest=600)
        kwargs[field] = value
        with pytest.raises(ValidationError):
            CustomerData(**kwargs)

    def test_invalid_time_window(self):
        with pytest.raises(ValidationError):
            CustomerData(id=1, name="客户A", lat=39.9, lon=116.4,
                         demand=50, service_time_min=15,
                         tw_earliest=700, tw_latest=600)

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            CustomerData(id=1, name="", lat=39.9, lon=116.4,
                         demand=50, service_time_min=15,
                         tw_earliest=500, tw_latest=600)


# =========================================================================
# VehicleConfigItem
# =========================================================================

class TestVehicleConfigItem:
    def test_valid(self):
        v = VehicleConfigItem(capacity=800, fixed_cost=200.0,
                               fuel_per_100km=12.0, speed_kmh=40.0, count=3)
        assert v.capacity == 800
        assert v.fixed_cost == 200.0
        assert v.fuel_per_100km == 12.0
        assert v.speed_kmh == 40.0
        assert v.count == 3
        assert v.color == "#1f77b4"  # default

    def test_zero_values_allowed(self):
        """capacity=0, count=0 是允许的 (ge=0)。"""
        v = VehicleConfigItem(capacity=0, fixed_cost=0.0,
                               fuel_per_100km=0.0, speed_kmh=1.0, count=0)
        assert v.capacity == 0
        assert v.count == 0

    def test_zero_speed_rejected(self):
        """speed_kmh 必须是 gt=0。"""
        with pytest.raises(ValidationError):
            VehicleConfigItem(capacity=800, fixed_cost=200.0,
                               fuel_per_100km=12.0, speed_kmh=0.0, count=3)

    def test_negative_speed_rejected(self):
        with pytest.raises(ValidationError):
            VehicleConfigItem(capacity=800, fixed_cost=200.0,
                               fuel_per_100km=12.0, speed_kmh=-1.0, count=3)


# =========================================================================
# SolverParams
# =========================================================================

class TestSolverParams:
    def test_defaults(self):
        p = SolverParams()
        assert p.fuel_price == 7.5
        assert p.hourly_wage == 50.0
        assert p.carbon_price == 0.08
        assert p.late_penalty_per_min == 10.0
        assert p.search_time_limit == 30
        assert p.use_multi_strategy is True
        assert p.use_parallel is True

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("search_time_limit", 0), ("search_time_limit", 601),
            ("fuel_price", -1), ("hourly_wage", -1),
            ("carbon_price", -1), ("late_penalty_per_min", -1),
        ],
    )
    def test_invalid(self, field, value):
        with pytest.raises(ValidationError):
            SolverParams(**{field: value})

    def test_zero_values_allowed(self):
        """fuel_price=0, hourly_wage=0 等是允许的 (ge=0)。"""
        p = SolverParams(fuel_price=0, hourly_wage=0, carbon_price=0,
                          late_penalty_per_min=0)
        assert p.fuel_price == 0
        assert p.hourly_wage == 0

    def test_boundary_time_limit(self):
        SolverParams(search_time_limit=1)
        SolverParams(search_time_limit=600)


# =========================================================================
# SolveRequest
# =========================================================================

class TestSolveRequest:
    def _two_customers(self):
        return [
            CustomerData(id=0, name="仓库", lat=39.9, lon=116.4,
                         demand=0, service_time_min=0,
                         tw_earliest=0, tw_latest=1440),
            CustomerData(id=1, name="客户A", lat=39.91, lon=116.41,
                         demand=50, service_time_min=15,
                         tw_earliest=500, tw_latest=600),
        ]

    def test_empty_rejected(self):
        with pytest.raises(ValidationError):
            SolveRequest(customers=[])

    def test_single_customer_rejected(self):
        with pytest.raises(ValidationError):
            SolveRequest(customers=[self._two_customers()[0]])

    def test_valid_minimal(self):
        req = SolveRequest(customers=self._two_customers())
        assert len(req.customers) == 2
        assert req.vehicle_config is None
        assert req.params is None
        assert req.callback_url is None
        assert req.scenario_name is None

    def test_valid_with_all_fields(self):
        req = SolveRequest(
            customers=self._two_customers(),
            vehicle_config={
                "4.2m": VehicleConfigItem(capacity=800, fixed_cost=200.0,
                                          fuel_per_100km=12.0, speed_kmh=40.0, count=3),
            },
            params=SolverParams(fuel_price=8.0, search_time_limit=60),
            callback_url="https://example.com/callback",
            scenario_name="测试",
        )
        assert req.vehicle_config is not None
        assert "4.2m" in req.vehicle_config
        assert req.params.fuel_price == 8.0
        assert req.callback_url == "https://example.com/callback"
        assert req.scenario_name == "测试"


# =========================================================================
# ScenarioCreate & ScenarioUpdate
# =========================================================================

class TestScenarioCreate:
    def test_valid(self):
        sc = ScenarioCreate(
            name="测试场景",
            description="测试描述",
            customers=[
                {"id": 0, "name": "仓库", "lat": 39.9, "lon": 116.4,
                 "demand": 0, "service_time_min": 0,
                 "tw_earliest": 0, "tw_latest": 1440},
                {"id": 1, "name": "客户A", "lat": 39.91, "lon": 116.41,
                 "demand": 50, "service_time_min": 15,
                 "tw_earliest": 500, "tw_latest": 600},
            ],
        )
        assert sc.name == "测试场景"
        assert sc.description == "测试描述"
        assert len(sc.customers) == 2

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ScenarioCreate(name="",
                           customers=[{"id": 0, "name": "仓库", "lat": 39.9, "lon": 116.4,
                                       "demand": 0, "service_time_min": 0,
                                       "tw_earliest": 0, "tw_latest": 1440}])

    def test_optional_description(self):
        sc = ScenarioCreate(
            name="测试",
            customers=[{"id": 0, "name": "仓库", "lat": 39.9, "lon": 116.4,
                         "demand": 0, "service_time_min": 0,
                         "tw_earliest": 0, "tw_latest": 1440},
                       {"id": 1, "name": "a", "lat": 39.9, "lon": 116.4,
                         "demand": 1, "service_time_min": 1,
                         "tw_earliest": 0, "tw_latest": 100}],
        )
        assert sc.description is None


class TestScenarioUpdate:
    def test_partial(self):
        su = ScenarioUpdate(name="新名称")
        assert su.name == "新名称"
        assert su.description is None

    def test_full(self):
        su = ScenarioUpdate(name="新名称", description="新描述",
                             customers=[{"id": 0, "name": "仓库", "lat": 39.9, "lon": 116.4,
                                         "demand": 0, "service_time_min": 0,
                                         "tw_earliest": 0, "tw_latest": 1440}])
        assert su.name == "新名称"
        assert su.description == "新描述"
        assert len(su.customers) == 1

    def test_empty_allowed(self):
        """所有字段均为 None 是允许的。"""
        su = ScenarioUpdate()
        assert su.name is None
        assert su.description is None
