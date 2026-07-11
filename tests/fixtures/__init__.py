"""Fixtures package for tests."""

from .customers import (
    get_invalid_customers_df,
    get_minimal_solution,
    get_test_customers_df,
    get_test_params,
    get_test_vehicle_config,
)

__all__ = [
    "get_test_customers_df",
    "get_test_vehicle_config",
    "get_test_params",
    "get_minimal_solution",
    "get_invalid_customers_df",
]
