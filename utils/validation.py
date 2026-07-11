"""
数据验证工具函数

提供输入数据的验证功能。
"""

from typing import Any

from config.constants import DEFAULT_PARAMS
from exceptions.errors import ValidationError


def validate_customer(customer: dict[str, Any]) -> None:
    """
    验证客户数据。

    Args:
        customer: 客户数据字典

    Raises:
        ValidationError: 数据验证失败
    """
    required_fields = ["id", "lat", "lon"]

    for field in required_fields:
        if field not in customer:
            raise ValidationError(
                f"缺少必需字段: {field}",
                field=field,
            )

    # 验证 ID
    if not isinstance(customer["id"], int) or isinstance(customer["id"], bool):
        raise ValidationError(
            "ID 必须为数字",
            field="id",
            value=customer["id"],
        )

    # 验证坐标
    lat = customer["lat"]
    lon = customer["lon"]

    if not isinstance(lat, (int, float)):
        raise ValidationError(
            "纬度必须为数字",
            field="lat",
            value=lat,
        )

    if not isinstance(lon, (int, float)):
        raise ValidationError(
            "经度必须为数字",
            field="lon",
            value=lon,
        )

    if lat < -90 or lat > 90:
        raise ValidationError(
            "纬度必须在 -90 到 90 之间",
            field="lat",
            value=lat,
        )

    if lon < -180 or lon > 180:
        raise ValidationError(
            "经度必须在 -180 到 180 之间",
            field="lon",
            value=lon,
        )

    # 验证需求量
    if "demand" in customer:
        demand = customer["demand"]
        if not isinstance(demand, (int, float)) or demand < 0:
            raise ValidationError(
                "需求量必须为非负数",
                field="demand",
                value=demand,
            )

    # 验证时间窗
    if "tw_earliest" in customer and "tw_latest" in customer:
        earliest = customer["tw_earliest"]
        latest = customer["tw_latest"]

        # 验证时间窗非负
        if earliest < 0 or latest < 0:
            raise ValidationError(
                "时间窗分钟数不能为负数",
                field="time_window",
                details={"tw_earliest": earliest, "tw_latest": latest},
            )

        if earliest >= latest:
            raise ValidationError(
                "时间窗最早时间必须小于最晚时间",
                field="time_window",
                details={"tw_earliest": earliest, "tw_latest": latest},
            )


def validate_customers(customers: list[dict[str, Any]]) -> None:
    """
    验证客户列表。

    Args:
        customers: 客户列表

    Raises:
        ValidationError: 数据验证失败
    """
    if not customers:
        raise ValidationError("客户列表不能为空")

    for i, customer in enumerate(customers):
        try:
            validate_customer(customer)
        except ValidationError as e:
            raise ValidationError(
                f"客户 {i} 数据无效: {e.message}",
                field=e.details.get("field"),
                value=e.details.get("value"),
                details={**e.details, "customer_index": i},
            ) from e


def validate_vehicle_config(vehicle_config: dict[str, Any]) -> None:
    """
    验证车型配置。

    Args:
        vehicle_config: 车型配置字典

    Raises:
        ValidationError: 数据验证失败
    """
    if not vehicle_config:
        raise ValidationError("车型配置不能为空")

    required_fields = ["capacity", "fixed_cost", "fuel_per_100km"]

    for vehicle_type, config in vehicle_config.items():
        if not isinstance(config, dict):
            raise ValidationError(
                f"车型 {vehicle_type} 配置必须为字典",
                field=vehicle_type,
            )

        for field in required_fields:
            if field not in config:
                raise ValidationError(
                    f"车型 {vehicle_type} 缺少必需字段: {field}",
                    field=field,
                )

        # 验证数值
        if config.get("capacity", 0) <= 0:
            raise ValidationError(
                f"车型 {vehicle_type} 载重量必须为正数",
                field="capacity",
                value=config.get("capacity"),
            )

        if config.get("fixed_cost", 0) < 0:
            raise ValidationError(
                f"车型 {vehicle_type} 固定成本不能为负数",
                field="fixed_cost",
                value=config.get("fixed_cost"),
            )

        if config.get("fuel_per_100km", 0) <= 0:
            raise ValidationError(
                f"车型 {vehicle_type} 油耗必须为正数",
                field="fuel_per_100km",
                value=config.get("fuel_per_100km"),
            )


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    """
    验证全局参数并填充默认值。

    Args:
        params: 参数字典

    Returns:
        验证后的参数字典（包含默认值）

    Raises:
        ValidationError: 数据验证失败
    """
    # 使用默认值填充缺失参数
    validated = {**DEFAULT_PARAMS, **params}

    # 验证数值参数
    numeric_params = {
        "fuel_price": (0, float("inf"), "油价"),
        "hourly_wage": (0, float("inf"), "时薪"),
        "carbon_price": (0, float("inf"), "碳价"),
        "late_penalty_per_min": (0, float("inf"), "迟到罚金"),
    }

    for param, (min_val, max_val, name) in numeric_params.items():
        value = validated.get(param)
        if value is not None:
            if not isinstance(value, (int, float)):
                raise ValidationError(
                    f"{name}必须为数字",
                    field=param,
                    value=value,
                )
            if value < min_val or value > max_val:
                raise ValidationError(
                    f"{name}必须在 {min_val} 到 {max_val} 之间",
                    field=param,
                    value=value,
                )

    return validated


def validate_solve_request(
    customers: list[dict[str, Any]],
    vehicle_config: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    验证求解请求。

    Args:
        customers: 客户列表
        vehicle_config: 车型配置
        params: 全局参数

    Returns:
        验证后的参数字典

    Raises:
        ValidationError: 数据验证失败
    """
    validate_customers(customers)
    validate_vehicle_config(vehicle_config)

    params = validate_params(params) if params else DEFAULT_PARAMS.copy()

    return params
