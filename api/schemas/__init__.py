# API Schemas Module
"""
Pydantic 数据模型：请求和响应的数据契约
"""

from .request import (
    CustomerData,
    ScenarioCreate,
    ScenarioUpdate,
    SolveRequest,
    SolverParams,
    VehicleConfigItem,
)
from .response import (
    CostData,
    HealthResponse,
    JobStatusResponse,
    RouteData,
    ScenarioDetailResponse,
    ScenarioResponse,
    SolutionData,
    SolveResponse,
    StopData,
)

__all__ = [
    # Request
    "SolveRequest",
    "CustomerData",
    "VehicleConfigItem",
    "SolverParams",
    "ScenarioCreate",
    "ScenarioUpdate",
    # Response
    "SolveResponse",
    "SolutionData",
    "CostData",
    "RouteData",
    "StopData",
    "ScenarioResponse",
    "ScenarioDetailResponse",
    "JobStatusResponse",
    "HealthResponse",
]
