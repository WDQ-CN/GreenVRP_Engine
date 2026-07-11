"""
单元测试：api/schemas/request.py
"""

import pytest
from pydantic import ValidationError

from api.schemas.request import CustomerData, SolveRequest, SolverParams, VehicleConfigItem


class TestCustomerData:
    def test_valid_customer(self):
        c = CustomerData(
            id=1,
            name="客户A",
            lat=39.9,
            lon=116.4,
            demand=50,
            service_time_min=15,
            tw_earliest=500,
            tw_latest=600,
        )
        assert c.id == 1

    def test_invalid_time_window(self):
        with pytest.raises(ValidationError):
            CustomerData(
                id=1,
                name="客户A",
                lat=39.9,
                lon=116.4,
                demand=50,
                service_time_min=15,
                tw_earliest=700,
                tw_latest=600,
            )

    def test_lat_out_of_range(self):
        with pytest.raises(ValidationError):
            CustomerData(
                id=1,
                name="客户A",
                lat=95.0,
                lon=116.4,
                demand=50,
                service_time_min=15,
                tw_earliest=500,
                tw_latest=600,
            )


class TestVehicleConfigItem:
    def test_valid_config(self):
        v = VehicleConfigItem(
            capacity=800,
            fixed_cost=200.0,
            fuel_per_100km=12.0,
            speed_kmh=40.0,
            count=3,
        )
        assert v.capacity == 800

    def test_negative_capacity(self):
        with pytest.raises(ValidationError):
            VehicleConfigItem(
                capacity=-1,
                fixed_cost=200.0,
                fuel_per_100km=12.0,
                speed_kmh=40.0,
                count=3,
            )

    def test_zero_speed(self):
        with pytest.raises(ValidationError):
            VehicleConfigItem(
                capacity=800,
                fixed_cost=200.0,
                fuel_per_100km=12.0,
                speed_kmh=0.0,
                count=3,
            )


class TestSolverParams:
    def test_default_values(self):
        p = SolverParams()
        assert p.fuel_price == 7.5
        assert p.search_time_limit == 30

    def test_time_limit_too_large(self):
        with pytest.raises(ValidationError):
            SolverParams(search_time_limit=601)


class TestSolveRequest:
    def test_min_customers(self):
        with pytest.raises(ValidationError):
            SolveRequest(customers=[])

    def test_valid_request(self):
        req = SolveRequest(
            customers=[
                CustomerData(
                    id=0,
                    name="仓库",
                    lat=39.9,
                    lon=116.4,
                    demand=0,
                    service_time_min=0,
                    tw_earliest=0,
                    tw_latest=1440,
                ),
                CustomerData(
                    id=1,
                    name="客户A",
                    lat=39.91,
                    lon=116.41,
                    demand=50,
                    service_time_min=15,
                    tw_earliest=500,
                    tw_latest=600,
                ),
            ]
        )
        assert req.scenario_name is None
