"""
单元测试：utils/validation.py — 数据验证
"""

import pytest
from exceptions.errors import ValidationError
from utils.validation import (
    validate_customer,
    validate_customers,
    validate_params,
    validate_solve_request,
    validate_vehicle_config,
)


class TestValidateCustomer:
    def test_valid(self):
        validate_customer({"id": 1, "lat": 39.9, "lon": 116.4})

    def test_missing_id(self):
        with pytest.raises(ValidationError, match="id"):
            validate_customer({"lat": 39.9, "lon": 116.4})

    def test_missing_lat(self):
        with pytest.raises(ValidationError):
            validate_customer({"id": 1, "lon": 116.4})

    def test_invalid_id_type(self):
        with pytest.raises(ValidationError):
            validate_customer({"id": "abc", "lat": 39.9, "lon": 116.4})

    def test_lat_out_of_range(self):
        with pytest.raises(ValidationError):
            validate_customer({"id": 1, "lat": 95.0, "lon": 116.4})

    def test_lon_out_of_range(self):
        with pytest.raises(ValidationError):
            validate_customer({"id": 1, "lat": 39.9, "lon": 181.0})

    def test_negative_demand(self):
        with pytest.raises(ValidationError):
            validate_customer({"id": 1, "lat": 39.9, "lon": 116.4, "demand": -1})

    def test_invalid_time_window(self):
        with pytest.raises(ValidationError):
            validate_customer({"id": 1, "lat": 39.9, "lon": 116.4,
                               "tw_earliest": 700, "tw_latest": 600})

    def test_negative_time_window(self):
        with pytest.raises(ValidationError):
            validate_customer({"id": 1, "lat": 39.9, "lon": 116.4,
                               "tw_earliest": -1, "tw_latest": 600})


class TestValidateCustomers:
    def test_valid_list(self):
        validate_customers([
            {"id": 1, "lat": 39.9, "lon": 116.4},
            {"id": 2, "lat": 40.0, "lon": 116.5},
        ])

    def test_empty_list(self):
        with pytest.raises(ValidationError, match="不能为空"):
            validate_customers([])

    def test_invalid_item(self):
        with pytest.raises(ValidationError):
            validate_customers([
                {"id": 1, "lat": 39.9, "lon": 116.4},
                {"id": "bad", "lat": 40.0, "lon": 116.5},
            ])


class TestValidateVehicleConfig:
    def test_valid(self):
        validate_vehicle_config({
            "4.2m": {"capacity": 800, "fixed_cost": 200, "fuel_per_100km": 12},
        })

    def test_empty(self):
        with pytest.raises(ValidationError, match="不能为空"):
            validate_vehicle_config({})

    def test_missing_capacity(self):
        with pytest.raises(ValidationError):
            validate_vehicle_config({
                "4.2m": {"fixed_cost": 200, "fuel_per_100km": 12},
            })

    def test_zero_capacity(self):
        with pytest.raises(ValidationError):
            validate_vehicle_config({
                "4.2m": {"capacity": 0, "fixed_cost": 200, "fuel_per_100km": 12},
            })

    def test_negative_fixed_cost(self):
        with pytest.raises(ValidationError):
            validate_vehicle_config({
                "4.2m": {"capacity": 800, "fixed_cost": -1, "fuel_per_100km": 12},
            })

    def test_not_dict(self):
        with pytest.raises(ValidationError):
            validate_vehicle_config({"4.2m": "not-a-dict"})


class TestValidateParams:
    def test_defaults(self):
        result = validate_params({})
        assert result["fuel_price"] == 7.5
        assert result["hourly_wage"] == 50.0

    def test_override(self):
        result = validate_params({"fuel_price": 8.0})
        assert result["fuel_price"] == 8.0
        assert result["hourly_wage"] == 50.0  # default

    def test_negative_fuel_price(self):
        with pytest.raises(ValidationError):
            validate_params({"fuel_price": -1})

    def test_non_numeric(self):
        with pytest.raises(ValidationError):
            validate_params({"fuel_price": "abc"})


class TestValidateSolveRequest:
    def test_valid(self):
        result = validate_solve_request(
            customers=[{"id": 1, "lat": 39.9, "lon": 116.4}],
            vehicle_config={"4.2m": {"capacity": 800, "fixed_cost": 200,
                                      "fuel_per_100km": 12}},
        )
        assert result["fuel_price"] == 7.5

    def test_empty_customers(self):
        with pytest.raises(ValidationError):
            validate_solve_request(
                customers=[],
                vehicle_config={"4.2m": {"capacity": 800, "fixed_cost": 200,
                                          "fuel_per_100km": 12}},
            )

    def test_params_override(self):
        result = validate_solve_request(
            customers=[{"id": 1, "lat": 39.9, "lon": 116.4}],
            vehicle_config={"4.2m": {"capacity": 800, "fixed_cost": 200,
                                      "fuel_per_100km": 12}},
            params={"fuel_price": 9.0},
        )
        assert result["fuel_price"] == 9.0
