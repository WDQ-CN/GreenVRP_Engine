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
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np

from data_types.cost import CostDict
from config.constants import DIESEL_CO2_FACTOR
from exceptions.errors import CostCalculationError, ValidationError

# 默认碳交易价格（元/kg）
DEFAULT_CARBON_PRICE: float = 0.08

# 车型参数缓存（使用LRU缓存避免内存泄漏）
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
    vehicle_config: Dict[str, Dict[str, Any]],
) -> Dict[str, VehicleCostParams]:
    """
    预构建车型成本参数，避免重复计算。

    Args:
        vehicle_config: 原始车型配置

    Returns:
        车型成本参数字典
    """
    params = {}
    for v_type, config in vehicle_config.items():
        if not isinstance(config, dict):
            continue  # 跳过无效配置
        fuel_per_100km = config.get("fuel_per_100km", 12)
        fixed_cost = config.get("fixed_cost", 0)
        speed_kmh = config.get("speed_kmh", 40)

        # 类型安全检查：确保数值类型
        try:
            fuel_per_100km = float(fuel_per_100km)
            fixed_cost = float(fixed_cost)
            speed_kmh = float(speed_kmh)
        except (TypeError, ValueError):
            fuel_per_100km = 12.0
            fixed_cost = 0.0
            speed_kmh = 40.0

        params[v_type] = VehicleCostParams(
            vehicle_type=v_type,
            fixed_cost=fixed_cost,
            fuel_per_100km=fuel_per_100km,
            speed_kmh=speed_kmh,
            fuel_coefficient=fuel_per_100km / 100.0,
            carbon_coefficient=fuel_per_100km / 100.0 * DIESEL_CO2_FACTOR,
        )
    return params


def _get_vehicle_params_cached(
    vehicle_config: Dict[str, Dict[str, Any]],
) -> Dict[str, VehicleCostParams]:
    """
    获取缓存的车型参数。

    使用LRU缓存策略，避免内存泄漏。

    Args:
        vehicle_config: 车型配置

    Returns:
        车型成本参数字典
    """
    # 使用内部的LRU缓存实现
    return _get_vehicle_params_cached_impl(_make_config_key(vehicle_config), vehicle_config)


def _make_config_key(vehicle_config: Dict[str, Dict[str, Any]]) -> int:
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


# 内部缓存存储（带大小限制）
_internal_cache: Dict[int, Dict[str, VehicleCostParams]] = {}
_cache_keys: List[int] = []  # 用于LRU淘汰


def _get_vehicle_params_cached_impl(
    config_key: int, vehicle_config: Dict[str, Dict[str, Any]]
) -> Dict[str, VehicleCostParams]:
    """带LRU淘汰的缓存实现。"""

    if config_key in _internal_cache:
        # 更新LRU顺序
        _cache_keys.remove(config_key)
        _cache_keys.append(config_key)
        return _internal_cache[config_key]

    # 缓存满时淘汰最久未使用的
    if len(_internal_cache) >= _VEHICLE_PARAMS_CACHE_MAX_SIZE:
        oldest_key = _cache_keys.pop(0)
        del _internal_cache[oldest_key]

    # 构建并缓存
    result = _build_vehicle_params(vehicle_config)
    _internal_cache[config_key] = result
    _cache_keys.append(config_key)
    return result


def _calculate_waiting_time_vectorized(stops: List[Dict[str, Any]]) -> float:
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


def _calc_route_transport_costs(
    routes: List[Dict[str, Any]],
    vehicle_params: Dict[str, VehicleCostParams],
    fuel_price: float,
) -> tuple:
    """计算运输变动成本和碳排放（单路线循环）。"""
    transport_cost = 0.0
    carbon_emission_kg = 0.0
    total_driving_time_min = 0.0
    total_service_time_min = 0.0
    total_waiting_time_min = 0.0

    for route in routes:
        if not isinstance(route, dict):
            continue  # 跳过无效路线
        v_type = route.get("vehicle_type")
        if not v_type or not isinstance(v_type, str):
            continue
        v_params = vehicle_params.get(v_type)
        if v_params is None:
            continue

        distance_km = route.get("distance_km", 0)
        try:
            distance_km = float(distance_km)
        except (TypeError, ValueError):
            distance_km = 0.0

        fuel_consumed = distance_km * v_params.fuel_coefficient
        transport_cost += fuel_consumed * fuel_price
        carbon_emission_kg += distance_km * v_params.carbon_coefficient

        driving_time = (distance_km / max(v_params.speed_kmh, 0.1)) * 60
        total_driving_time_min += driving_time

        stops = route.get("stops")
        if not isinstance(stops, (list, tuple)):
            continue
        service_times = [
            s.get("service_time_min", s.get("service_time", 0))
            for s in stops if isinstance(s, dict) and s.get("node", 0) > 0
        ]
        total_service_time_min += sum(service_times)
        total_waiting_time_min += _calculate_waiting_time_vectorized(stops)

    return transport_cost, carbon_emission_kg, total_driving_time_min, total_service_time_min, total_waiting_time_min


def _calc_labor_cost(
    driving_time: float, service_time: float, waiting_time: float, hourly_wage: float
) -> float:
    """计算人工时间成本。"""
    total_time = driving_time + service_time + waiting_time
    return (total_time / 60) * hourly_wage


def _calc_fixed_cost(
    vehicles_used: Dict[str, int],
    vehicle_params: Dict[str, VehicleCostParams],
) -> float:
    """计算车辆固定成本。"""
    return sum(
        count * vehicle_params[v_type].fixed_cost
        for v_type, count in vehicles_used.items()
        if v_type in vehicle_params
    )


def _calc_penalty_cost(solution: Dict[str, Any], late_penalty: float) -> float:
    """计算违约惩罚成本。"""
    return solution.get("total_late_minutes", 0) * late_penalty


def _calc_carbon_cost(carbon_emission_kg: float, carbon_price: float) -> float:
    """计算碳排放成本。"""
    return carbon_emission_kg * carbon_price


def _build_cost_result(
    transport_cost: float, labor_cost: float, fixed_cost: float,
    penalty_cost: float, carbon_cost: float, carbon_emission_kg: float,
    total_driving_time_min: float, total_service_time_min: float,
    total_waiting_time_min: float, total_distance: float,
    total_cost: float,
) -> CostDict:
    """构建成本结果字典。"""
    return {
        "transport_cost": round(transport_cost, 2),
        "labor_cost": round(labor_cost, 2),
        "fixed_cost": round(fixed_cost, 2),
        "penalty_cost": round(penalty_cost, 2),
        "carbon_cost": round(carbon_cost, 2),
        "total_cost": round(total_cost, 2),
        "carbon_emission_kg": round(carbon_emission_kg, 2),
        "total_distance_km": total_distance,
        "total_time_min": round(total_driving_time_min + total_service_time_min + total_waiting_time_min, 1),
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


def calculate_green_cost(
    solution: Dict[str, Any],
    vehicle_config: Dict[str, Dict[str, Any]],
    params: Dict[str, float],
) -> CostDict:
    """
    计算五维绿色成本（性能优化版 v2）。

    使用 NumPy 向量化计算，显著提升大规模数据的处理速度。

    Args:
        solution: 求解器返回的解，包含 routes, vehicles_used, total_late_minutes 等
        vehicle_config: 车型配置字典
        params: 全局参数字典

    Returns:
        成本明细字典，包含五维成本及碳排放量
    """
    # ── 输入验证 ──────────────────────────────────────────────
    if not isinstance(solution, dict):
        raise ValidationError("solution 必须是字典类型", field="solution", value=type(solution).__name__)
    if not isinstance(vehicle_config, dict):
        raise ValidationError("vehicle_config 必须是字典类型", field="vehicle_config", value=type(vehicle_config).__name__)
    if not isinstance(params, dict):
        raise ValidationError("params 必须是字典类型", field="params", value=type(params).__name__)

    routes = solution.get("routes")
    if not isinstance(routes, (list, tuple)):
        raise ValidationError(
            "solution.routes 必须是列表类型",
            field="solution.routes",
            value=type(routes).__name__,
        )
    vehicles_used = solution.get("vehicles_used", {})
    if not isinstance(vehicles_used, dict):
        vehicles_used = {}  # 容错：非字典类型降级为空字典

    try:
        return _calculate_green_cost_impl(solution, vehicle_config, params, routes, vehicles_used)
    except (ValidationError, CostCalculationError):
        raise
    except Exception as e:
        raise CostCalculationError(
            message=f"成本计算内部错误: {e}",
            cost_type="综合",
            details={"error": str(e)},
        ) from e


def _calculate_green_cost_impl(
    solution: Dict[str, Any],
    vehicle_config: Dict[str, Dict[str, Any]],
    params: Dict[str, float],
    routes: List[Dict[str, Any]],
    vehicles_used: Dict[str, int],
) -> CostDict:
    """成本计算核心实现（异常安全分离）。"""
    fuel_price = params.get("fuel_price", 7.5)
    hourly_wage = params.get("hourly_wage", 50.0)
    carbon_price = params.get("carbon_price", DEFAULT_CARBON_PRICE)
    late_penalty = params.get("late_penalty_per_min", 10.0)

    vehicle_params = _get_vehicle_params_cached(vehicle_config)

    # 1. 运输成本 + 碳排放 + 时间统计
    transport_cost, carbon_emission_kg, driving_time, service_time, waiting_time = \
        _calc_route_transport_costs(routes, vehicle_params, fuel_price)

    # 2. 人工时间成本
    labor_cost = _calc_labor_cost(driving_time, service_time, waiting_time, hourly_wage)

    # 3. 车辆固定成本
    fixed_cost = _calc_fixed_cost(vehicles_used, vehicle_params)

    # 4. 违约惩罚成本
    penalty_cost = _calc_penalty_cost(solution, late_penalty)

    # 5. 碳排放成本
    carbon_cost = _calc_carbon_cost(carbon_emission_kg, carbon_price)

    total_cost = transport_cost + labor_cost + fixed_cost + penalty_cost + carbon_cost

    return _build_cost_result(
        transport_cost, labor_cost, fixed_cost, penalty_cost, carbon_cost,
        carbon_emission_kg, driving_time, service_time, waiting_time,
        solution.get("total_distance", 0), total_cost,
    )


def calculate_green_cost_batch(
    solutions: List[Dict[str, Any]],
    vehicle_config: Dict[str, Dict[str, Any]],
    params: Dict[str, float],
) -> List[Dict[str, Any]]:
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
    results = []
    for i, sol in enumerate(solutions):
        try:
            results.append(calculate_green_cost(sol, vehicle_config, params))
        except (ValidationError, CostCalculationError) as e:
            logger = __import__("logging").getLogger("green_vrp.cost")
            logger.warning("批量成本计算第 %d 条失败: %s", i, e)
            results.append({
                "transport_cost": 0, "labor_cost": 0, "fixed_cost": 0,
                "penalty_cost": 0, "carbon_cost": 0, "total_cost": 0,
                "carbon_emission_kg": 0, "total_distance_km": 0,
                "total_time_min": 0, "driving_time_min": 0,
                "service_time_min": 0, "waiting_time_min": 0,
                "cost_breakdown": {
                    "运输变动成本": 0, "人工时间成本": 0,
                    "车辆固定成本": 0, "违约惩罚成本": 0, "碳排放成本": 0,
                },
            })
    return results


def format_cost_report(cost_result: Dict[str, Any]) -> str:
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
    cost_result: Dict[str, Any], solution: Dict[str, Any]
) -> Dict[str, float]:
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

    # 类型安全：确保数值
    try:
        total_cost = float(total_cost)
        total_distance = float(total_distance)
        total_time = float(total_time)
        service_time = float(service_time)
        carbon_emission = float(carbon_emission)
    except (TypeError, ValueError):
        pass

    # 计算客户数量
    routes = solution.get("routes")
    if not isinstance(routes, (list, tuple)):
        routes = []
    total_customers = sum(
        len([s for s in route.get("stops", []) if isinstance(s, dict) and s.get("node", 0) > 0])
        for route in routes if isinstance(route, dict)
    )

    return {
        "cost_per_km": round(total_cost / max(abs(total_distance), 1), 2),
        "cost_per_customer": round(total_cost / max(total_customers, 1), 2),
        "carbon_per_km": round(carbon_emission / max(abs(total_distance), 1), 4),
        "labor_efficiency": round(service_time / max(total_time, 1), 4),
    }
