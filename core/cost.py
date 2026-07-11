"""
五维成本核算模块（性能优化版 v2）

实现精细化的物流成本核算，包含运输变动成本、人工时间成本、
车辆固定成本、违约惩罚成本和碳排放环境成本。

碳排核算逻辑：
- 柴油燃烧碳排放系数：2.63 kg CO2/升
- 碳交易价格：约 0.08 元/kg（2024年国内碳市场均价）
- 大车单位载重碳排低：满载效率高，分摊的固定碳排放少
- 小车单位载重碳排高：灵活性高但单位能耗高

ESG 视角：通过碳排成本内部化，引导企业选择更环保的运输方案。

性能优化 v2：
- 等待时间计算向量化
- 车型参数缓存
- 批量处理路线数据
"""

from dataclasses import dataclass
from typing import Any

import numpy as np

from config.constants import DIESEL_CO2_FACTOR

# 默认碳交易价格（元/kg）
DEFAULT_CARBON_PRICE: float = 0.08

# 车型参数缓存最大条目数
_VEHICLE_PARAMS_CACHE_MAX_SIZE = 128


@dataclass
class VehicleCostParams:
    """车型成本参数数据类，用于高效计算。"""

    vehicle_type: str
    fixed_cost: float
    fuel_per_100km: float
    speed_kmh: float
    # 预计算的油耗系数（油耗/100）
    fuel_coefficient: float
    # 预计算的碳排放系数（油耗/100 * 2.63）
    carbon_coefficient: float


def _build_vehicle_params(
    vehicle_config: dict[str, dict[str, Any]],
) -> dict[str, VehicleCostParams]:
    """
    预构建车型成本参数，避免重复计算。

    Args:
        vehicle_config: 原始车型配置

    Returns:
        车型成本参数字典
    """
    params = {}
    for v_type, config in vehicle_config.items():
        fuel_per_100km = config.get("fuel_per_100km", 12)
        params[v_type] = VehicleCostParams(
            vehicle_type=v_type,
            fixed_cost=config.get("fixed_cost", 0),
            fuel_per_100km=fuel_per_100km,
            speed_kmh=config.get("speed_kmh", 40),
            fuel_coefficient=fuel_per_100km / 100.0,
            carbon_coefficient=fuel_per_100km / 100.0 * DIESEL_CO2_FACTOR,
        )
    return params


def _make_config_key(vehicle_config: dict[str, dict[str, Any]]) -> int:
    """生成配置哈希键。"""
    return hash(
        tuple(
            sorted(
                (
                    k,
                    tuple(
                        sorted(
                            (kk, vv)
                            for kk, vv in v.items()
                            if isinstance(vv, (int, float, str, bool))
                        )
                    ),
                )
                for k, v in vehicle_config.items()
            )
        )
    )


# 简化的车型参数缓存：字典 + 大小限制，替代手动 LRU+TTL 实现
# 相比之前的线程安全手动实现更简洁、易维护
_vehicle_params_cache: dict[int, dict[str, VehicleCostParams]] = {}


def _get_vehicle_params(vehicle_config: dict[str, dict[str, Any]]) -> dict[str, VehicleCostParams]:
    """
    获取缓存的车型参数。

    使用哈希键实现 O(1) 查找，缓存大小受 _VEHICLE_PARAMS_CACHE_MAX_SIZE 限制。

    Args:
        vehicle_config: 车型配置

    Returns:
        车型成本参数字典
    """
    config_key = _make_config_key(vehicle_config)

    if config_key not in _vehicle_params_cache:
        # 缓存满时淘汰最早存入的条目
        if len(_vehicle_params_cache) >= _VEHICLE_PARAMS_CACHE_MAX_SIZE:
            oldest_key = next(iter(_vehicle_params_cache))
            _vehicle_params_cache.pop(oldest_key, None)
        _vehicle_params_cache[config_key] = _build_vehicle_params(vehicle_config)

    return _vehicle_params_cache[config_key]


def _calculate_waiting_time_vectorized(stops: list[dict[str, Any]]) -> float:
    """
    向量化计算等待时间。

    使用 NumPy 向量化操作替代循环，提升计算效率。

    Args:
        stops: 站点列表

    Returns:
        总等待时间（分钟）
    """
    if not stops:
        return 0.0

    # 提取数组
    nodes = np.array([s.get("node", 0) for s in stops])
    arrivals = np.array([s.get("arrival_time", 0) for s in stops])
    tw_earliest = np.array([s.get("tw_earliest", 0) for s in stops])

    # 过滤客户节点（node > 0）
    mask = nodes > 0
    if not np.any(mask):
        return 0.0

    # 向量化计算等待时间
    waiting_times = np.maximum(0, tw_earliest[mask] - arrivals[mask])
    return float(np.sum(waiting_times))


def calculate_green_cost(
    solution: dict[str, Any],
    vehicle_config: dict[str, dict[str, Any]],
    params: dict[str, float],
) -> dict[str, Any]:
    """
    计算五维绿色成本（性能优化版 v2）。

    使用 NumPy 向量化计算，显著提升大规模数据的处理速度。

    Args:
        solution: 求解器返回的解，包含 routes, vehicles_used, total_late_minutes 等
        vehicle_config: 车型配置字典
        params: 全局参数字典，包含：
            - fuel_price: 油价（元/升）
            - hourly_wage: 时薪（元/小时）
            - carbon_price: 碳交易价格（元/kg）
            - late_penalty_per_min: 迟到罚金（元/分钟）

    Returns:
        成本明细字典，包含五维成本及碳排放量：
        - transport_cost: 运输变动成本（元）
        - labor_cost: 人工时间成本（元）
        - fixed_cost: 车辆固定成本（元）
        - penalty_cost: 违约惩罚成本（元）
        - carbon_cost: 碳排放环境成本（元）
        - total_cost: 总成本（元）
        - carbon_emission_kg: 碳排放量（kg）
        - total_distance_km: 总行驶距离（公里）

    Note:
        五维成本模型详解：

        1. 运输变动成本 = Σ(距离/100 × 车型油耗 × 油价)
           - 直接与行驶距离成正比
           - 大车油耗高但载重效率高，单位货物运费可能更低

        2. 人工时间成本 = Σ((行驶时间 + 卸货时间 + 等待时间) / 60 × 时薪)
           - 包含所有司机工作时间
           - 等待时间：早到需等待客户开门

        3. 车辆固定成本 = Σ(派发该车型数量 × 该车型发车费)
           - 包括折旧、保险、年检等固定成本
           - 大车固定成本高但单件分摊少

        4. 违约惩罚成本 = Σ(总迟到分钟数 × 罚金)
           - 迟到影响客户满意度
           - 软时间窗允许迟到但产生惩罚

        5. 碳排放成本 = Σ(距离/100 × 油耗 × 2.63kg/L × 碳价)
           - 碳排放内部化，体现 ESG 责任
           - 引导企业选择更环保的运输方案
    """
    # 提取参数
    fuel_price = params.get("fuel_price", 7.5)
    hourly_wage = params.get("hourly_wage", 50.0)
    carbon_price = params.get("carbon_price", DEFAULT_CARBON_PRICE)
    late_penalty = params.get("late_penalty_per_min", 10.0)

    # 使用缓存的车型参数
    vehicle_params = _get_vehicle_params(vehicle_config)

    # 初始化成本
    transport_cost = 0.0
    labor_cost = 0.0
    fixed_cost = 0.0
    penalty_cost = 0.0
    carbon_emission_kg = 0.0

    # 总时间统计
    total_driving_time_min = 0.0
    total_service_time_min = 0.0
    total_waiting_time_min = 0.0

    routes = solution.get("routes", [])
    vehicles_used = solution.get("vehicles_used", {})

    # ========== 1. 批量计算运输变动成本和碳排放 ==========
    for route in routes:
        v_type = route.get("vehicle_type")  # 修复：使用get避免KeyError
        if v_type is None:
            continue
        v_params = vehicle_params.get(v_type)

        if v_params is None:
            continue

        distance_km = route.get("distance_km", 0)

        # 运输变动成本 = 距离 × 油耗系数 × 油价
        fuel_consumed = distance_km * v_params.fuel_coefficient
        transport_cost += fuel_consumed * fuel_price

        # 碳排放 = 油耗 × 2.63 kg CO2/升
        carbon_emission_kg += distance_km * v_params.carbon_coefficient

        # 行驶时间 = 距离 / 速度 × 60
        driving_time = (distance_km / v_params.speed_kmh) * 60
        total_driving_time_min += driving_time

        # 批量处理站点数据
        stops = route.get("stops", [])

        # 使用列表推导式提取服务时间（修复：使用正确的字段名）
        service_times = [
            s.get("service_time_min", s.get("service_time", 0))
            for s in stops
            if s.get("node", 0) > 0
        ]
        total_service_time_min += sum(service_times)

        # 向量化计算等待时间
        total_waiting_time_min += _calculate_waiting_time_vectorized(stops)

    # ========== 2. 计算人工时间成本 ==========
    total_time_min = total_driving_time_min + total_service_time_min + total_waiting_time_min
    labor_cost = (total_time_min / 60) * hourly_wage

    # ========== 3. 计算车辆固定成本（向量化）==========
    fixed_cost = sum(
        count * vehicle_params[v_type].fixed_cost
        for v_type, count in vehicles_used.items()
        if v_type in vehicle_params
    )

    # ========== 4. 计算违约惩罚成本 ==========
    total_late_minutes = solution.get("total_late_minutes", 0)
    penalty_cost = total_late_minutes * late_penalty

    # ========== 5. 计算碳排放成本 ==========
    carbon_cost = carbon_emission_kg * carbon_price

    # 总成本
    total_cost = transport_cost + labor_cost + fixed_cost + penalty_cost + carbon_cost

    return {
        "transport_cost": round(transport_cost, 2),
        "labor_cost": round(labor_cost, 2),
        "fixed_cost": round(fixed_cost, 2),
        "penalty_cost": round(penalty_cost, 2),
        "carbon_cost": round(carbon_cost, 2),
        "total_cost": round(total_cost, 2),
        "carbon_emission_kg": round(carbon_emission_kg, 2),
        "total_distance_km": solution.get("total_distance", 0),
        "total_time_min": round(total_time_min, 1),
        "driving_time_min": round(total_driving_time_min, 1),
        "service_time_min": round(total_service_time_min, 1),
        "waiting_time_min": round(total_waiting_time_min, 1),
        "cost_breakdown": {
            "运输变动成本": round(transport_cost, 2),
            "人工时间成本": round(labor_cost, 2),
            "车辆固定成本": round(fixed_cost, 2),
            "违约惩罚成本": round(penalty_cost, 2),
            "碳排放成本": round(carbon_cost, 2),
        },
    }


def calculate_green_cost_batch(
    solutions: list[dict[str, Any]],
    vehicle_config: dict[str, dict[str, Any]],
    params: dict[str, float],
) -> list[dict[str, Any]]:
    """
    批量计算多个解的成本（高性能版本）。

    适用于需要对多个候选解进行成本评估的场景。

    Args:
        solutions: 求解结果列表
        vehicle_config: 车型配置
        params: 全局参数

    Returns:
        成本结果列表
    """
    return [calculate_green_cost(sol, vehicle_config, params) for sol in solutions]


def format_cost_report(cost_result: dict[str, Any]) -> str:
    """
    格式化成本报告为可读文本。

    Args:
        cost_result: calculate_green_cost 返回的结果字典

    Returns:
        格式化的成本报告字符串
    """
    report = []
    report.append("=" * 50)
    report.append("绿色物流成本核算报告")
    report.append("=" * 50)
    report.append(f"总成本: ¥{cost_result['total_cost']:,.2f}")
    report.append("-" * 50)
    report.append("成本明细:")
    for name, value in cost_result["cost_breakdown"].items():
        report.append(f"  {name}: ¥{value:,.2f}")
    report.append("-" * 50)
    report.append(f"碳排放量: {cost_result['carbon_emission_kg']:,.2f} kg CO2")
    report.append(f"总行驶距离: {cost_result['total_distance_km']:,.2f} km")
    report.append(f"总作业时间: {cost_result['total_time_min']:,.1f} 分钟")
    report.append("=" * 50)

    return "\n".join(report)


def calculate_cost_efficiency_metrics(
    cost_result: dict[str, Any], solution: dict[str, Any]
) -> dict[str, float]:
    """
    计算成本效率指标。

    用于评估物流运营效率，支持决策优化。

    Args:
        cost_result: 成本计算结果
        solution: 求解结果

    Returns:
        效率指标字典：
        - cost_per_km: 单位距离成本（元/公里）
        - cost_per_customer: 单位客户成本（元/客户）
        - carbon_per_km: 单位距离碳排放（kg/公里）
        - labor_efficiency: 人工效率（服务时间/总时间）
    """
    total_cost = cost_result.get("total_cost", 0)
    total_distance = cost_result.get("total_distance_km", 0)
    total_time = cost_result.get("total_time_min", 0)
    service_time = cost_result.get("service_time_min", 0)
    carbon_emission = cost_result.get("carbon_emission_kg", 0)

    # 计算客户数量
    routes = solution.get("routes", [])
    total_customers = sum(
        len([s for s in route.get("stops", []) if s.get("node", 0) > 0]) for route in routes
    )

    return {
        "cost_per_km": round(total_cost / max(total_distance, 1), 2),
        "cost_per_customer": round(total_cost / max(total_customers, 1), 2),
        "carbon_per_km": round(carbon_emission / max(total_distance, 1), 4),
        "labor_efficiency": round(service_time / max(total_time, 1), 4),
    }
