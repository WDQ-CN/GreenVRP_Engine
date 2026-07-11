"""
异常定义模块

定义项目中使用的异常类型。
"""

from typing import Any, Dict, Optional


class GreenVRPError(Exception):
    """
    GreenVRP 基础异常类。

    所有项目异常的基类，提供统一的错误处理接口。

    Attributes:
        message: 错误消息
        error_code: 错误代码
        details: 错误详情
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GREENVRP_ERROR"
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class SolverError(GreenVRPError):
    """
    求解器错误。

    当求解过程中发生错误时抛出。
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            error_code or "SOLVER_ERROR",
            details,
        )


class ValidationError(GreenVRPError):
    """
    数据验证错误。

    当输入数据验证失败时抛出。
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["value"] = str(value)
        super().__init__(
            message,
            "VALIDATION_ERROR",
            error_details,
        )


class ConfigurationError(GreenVRPError):
    """
    配置错误。

    当配置项缺失或无效时抛出。
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
        super().__init__(
            message,
            "CONFIGURATION_ERROR",
            error_details,
        )


class DistanceCalculationError(GreenVRPError):
    """
    距离计算错误。

    当距离计算过程中发生错误时抛出。
    """

    def __init__(
        self,
        message: str,
        lat1: Optional[float] = None,
        lon1: Optional[float] = None,
        lat2: Optional[float] = None,
        lon2: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if lat1 is not None:
            error_details["lat1"] = lat1
        if lon1 is not None:
            error_details["lon1"] = lon1
        if lat2 is not None:
            error_details["lat2"] = lat2
        if lon2 is not None:
            error_details["lon2"] = lon2
        super().__init__(
            message,
            "DISTANCE_CALCULATION_ERROR",
            error_details,
        )


class CostCalculationError(GreenVRPError):
    """
    成本计算错误。

    当成本计算过程中发生错误时抛出。
    """

    def __init__(
        self,
        message: str,
        cost_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if cost_type:
            error_details["cost_type"] = cost_type
        super().__init__(
            message,
            "COST_CALCULATION_ERROR",
            error_details,
        )


class TrackingError(GreenVRPError):
    """
    追踪错误。

    当车辆追踪过程中发生错误时抛出。
    """

    def __init__(
        self,
        message: str,
        vehicle_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if vehicle_id is not None:
            error_details["vehicle_id"] = vehicle_id
        super().__init__(
            message,
            "TRACKING_ERROR",
            error_details,
        )


class JobNotFoundError(GreenVRPError):
    """
    任务未找到错误。

    当请求的任务不存在时抛出。
    """

    def __init__(
        self,
        job_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        error_details["job_id"] = job_id
        super().__init__(
            f"任务未找到: {job_id}",
            "JOB_NOT_FOUND",
            error_details,
        )


class JobTimeoutError(GreenVRPError):
    """
    任务超时错误。

    当任务执行超时时抛出。
    """

    def __init__(
        self,
        job_id: str,
        timeout_seconds: float,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        error_details["job_id"] = job_id
        error_details["timeout_seconds"] = timeout_seconds
        super().__init__(
            f"任务执行超时: {job_id} (超时: {timeout_seconds}秒)",
            "JOB_TIMEOUT",
            error_details,
        )
