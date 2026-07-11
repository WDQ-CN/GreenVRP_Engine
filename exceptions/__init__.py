"""
异常模块

提供统一的异常层次结构。
"""

from exceptions.errors import (
    ConfigurationError,
    CostCalculationError,
    DistanceCalculationError,
    GreenVRPError,
    JobNotFoundError,
    JobTimeoutError,
    SolverError,
    TrackingError,
    ValidationError,
)

__all__ = [
    "GreenVRPError",
    "SolverError",
    "ValidationError",
    "ConfigurationError",
    "DistanceCalculationError",
    "CostCalculationError",
    "TrackingError",
    "JobNotFoundError",
    "JobTimeoutError",
]
