"""
碳感知路由优化模块

以碳排放为主要优化目标，支持碳预算约束，
计算碳效率指标，提供减排建议。
"""

import inspect
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config.constants import DIESEL_CO2_FACTOR, VEHICLE_CARBON_BASELINE
from core.cost import calculate_green_cost


@dataclass
class CarbonEfficiencyReport:
    """碳效率报告。"""

    total_carbon_kg: float
    """总碳排放量"""

    carbon_per_km: float
    """单位距离碳排放"""

    carbon_per_customer: float
    """单位客户碳排放"""

    carbon_per_kg_goods: float
    """单位货物碳排放"""

    vehicle_efficiency: Dict[str, float]
    """各车型碳效率"""

    reduction_potential: float
    """减排潜力"""

    recommendations: List[str]
    """减排建议"""

    comparison_with_baseline: Optional[Dict[str, float]] = None
    """与基准对比"""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "total_carbon_kg": round(self.total_carbon_kg, 2),
            "carbon_per_km": round(self.carbon_per_km, 4),
            "carbon_per_customer": round(self.carbon_per_customer, 4),
            "carbon_per_kg_goods": round(self.carbon_per_kg_goods, 6),
            "vehicle_efficiency": {k: round(v, 4) for k, v in self.vehicle_efficiency.items()},
            "reduction_potential": round(self.reduction_potential, 2),
            "recommendations": self.recommendations,
            "comparison_with_baseline": self.comparison_with_baseline,
        }


class CarbonAwareOptimizer:
    """碳感知路由优化器。"""

    def __init__(
        self,
        solver_func,
        customers: List[Dict[str, Any]],
        vehicle_config: Dict[str, Dict[str, Any]],
        params: Dict[str, float],
    ):
        """
        初始化碳感知优化器。

        Args:
            solver_func: 求解函数，支持两种签名：
                - 新签名: (customers_df, vehicle_config, time_penalty_per_min, time_limit)
                - 旧签名: (customers, vehicle_config, params)
            customers: 客户数据
            vehicle_config: 车型配置
            params: 全局参数
        """
        self.solver_func = solver_func
        self.customers = customers
        self.vehicle_config = vehicle_config
        self.params = params
        # 检测求解器函数签名
        self._solver_signature = self._detect_solver_signature()

    def _detect_solver_signature(self) -> str:
        """检测求解器函数签名类型。"""
        try:
            sig = inspect.signature(self.solver_func)
            params = list(sig.parameters.keys())
            # 新签名: customers_df, vehicle_config, time_penalty_per_min, time_limit
            if len(params) >= 2 and ("time_penalty" in str(params) or "time_limit" in str(params)):
                return "new"
            # 旧签名: customers, vehicle_config, params
            return "old"
        except Exception:
            return "old"

    def _call_solver(
        self,
        params: Optional[Dict[str, float]] = None,
        time_limit: int = 60,
    ) -> Dict[str, Any]:
        """
        调用求解器并计算成本数据。

        Args:
            params: 参数字典（用于旧签名求解器）
            time_limit: 时间限制

        Returns:
            包含 cost_data 的求解结果
        """
        use_params = params or self.params

        if self._solver_signature == "new":
            # 新签名: (customers_df, vehicle_config, time_penalty_per_min, time_limit)
            time_penalty = use_params.get("late_penalty_per_min", 10.0)
            # 将 customers 转换为 DataFrame
            if isinstance(self.customers, list):
                customers_df = pd.DataFrame(self.customers)
            else:
                customers_df = self.customers

            result = self.solver_func(
                customers_df,
                self.vehicle_config,
                time_penalty,
                time_limit,
            )
        else:
            # 旧签名: (customers, vehicle_config, params)
            result = self.solver_func(
                self.customers,
                self.vehicle_config,
                use_params,
            )

        # 确保结果包含 cost_data
        if "cost_data" not in result and "routes" in result:
            # 构建 params 字典
            cost_params = {
                "carbon_price": use_params.get("carbon_price", 0.08),
                "fuel_price": use_params.get("fuel_price", 7.5),
                "hourly_wage": use_params.get("labor_cost_per_hour", 30),
                "late_penalty_per_min": use_params.get("late_penalty_per_min", 10.0),
            }
            cost_result = calculate_green_cost(
                result,
                self.vehicle_config,
                cost_params,
            )
            result["cost_data"] = cost_result

        return result

    def optimize_for_carbon(
        self,
        carbon_target: Optional[float] = None,
        method: str = "weighted",
        time_limit: int = 60,
    ) -> Dict[str, Any]:
        """
        以碳排放为主要目标优化。

        Args:
            carbon_target: 碳排放目标（kg），None 则无约束
            method: 优化方法
                - "weighted": 加权法
                - "constraint": 约束法
                - "hierarchical": 层次法
            time_limit: 时间限制

        Returns:
            优化结果
        """
        if method == "weighted":
            return self._optimize_weighted(carbon_target, time_limit)
        elif method == "constraint":
            return self._optimize_constraint(carbon_target, time_limit)
        elif method == "hierarchical":
            return self._optimize_hierarchical(carbon_target, time_limit)
        else:
            raise ValueError(f"未知优化方法: {method}")

    def _optimize_weighted(
        self,
        carbon_target: Optional[float],
        time_limit: int,
    ) -> Dict[str, Any]:
        """
        加权法：将碳排放作为优化目标之一。
        """
        # 调整参数，大幅提高碳价权重
        adjusted_params = self.params.copy()
        base_carbon_price = self.params.get("carbon_price", 0.08)

        # 大幅提高碳价以强调碳减排
        adjusted_params["carbon_price"] = base_carbon_price * 10

        # 如果有碳排放目标，进一步提高权重
        if carbon_target is not None:
            adjusted_params["carbon_price"] = base_carbon_price * 20

        result = self._call_solver(adjusted_params, time_limit)

        result["optimization_method"] = "carbon_weighted"
        result["carbon_target"] = carbon_target

        # 检查是否达到目标
        actual_carbon = result.get("cost_data", {}).get("carbon_emission_kg", 0)
        if carbon_target is not None and actual_carbon > carbon_target:
            result["carbon_target_met"] = False
            result["carbon_gap"] = actual_carbon - carbon_target
        else:
            result["carbon_target_met"] = True
            result["carbon_gap"] = 0

        return result

    def _optimize_constraint(
        self,
        carbon_target: Optional[float],
        time_limit: int,
    ) -> Dict[str, Any]:
        """
        约束法：将碳排放作为硬约束。
        """
        if carbon_target is None:
            # 无约束，使用加权法
            return self._optimize_weighted(None, time_limit)

        # 尝试不同的碳价，找到满足约束的解
        carbon_prices = [0.5, 1.0, 2.0, 5.0, 10.0]

        best_result = None
        best_carbon = float("inf")

        for carbon_price in carbon_prices:
            adjusted_params = self.params.copy()
            adjusted_params["carbon_price"] = carbon_price

            result = self._call_solver(adjusted_params, time_limit)

            actual_carbon = result.get("cost_data", {}).get("carbon_emission_kg", 0)

            if actual_carbon <= carbon_target:
                if best_result is None or actual_carbon < best_carbon:
                    best_result = result
                    best_carbon = actual_carbon

            if actual_carbon < carbon_target * 0.8:
                # 已经明显低于目标，无需更高碳价
                break

        if best_result is None:
            # 无法满足碳约束
            result = self._call_solver(self.params, time_limit)
            result["carbon_target_met"] = False
            result["carbon_target"] = carbon_target
            result["message"] = "无法在给定碳约束下找到可行解"
        else:
            best_result["carbon_target_met"] = True
            best_result["carbon_target"] = carbon_target
            best_result["optimization_method"] = "carbon_constraint"

        return best_result if best_result is not None else result

    def _optimize_hierarchical(
        self,
        carbon_target: Optional[float],
        time_limit: int,
    ) -> Dict[str, Any]:
        """
        层次法：先优化碳排放，再在满足碳排放约束下优化成本。
        """
        # 第一阶段：最小化碳排放
        carbon_optimized = self._optimize_weighted(carbon_target, time_limit // 2)

        min_carbon = carbon_optimized.get("cost_data", {}).get("carbon_emission_kg", 0)

        if carbon_target is not None and min_carbon > carbon_target:
            # 无法达到碳目标
            carbon_optimized["carbon_target_met"] = False
            return carbon_optimized

        # 第二阶段：在碳约束下优化成本
        effective_target = min(carbon_target or min_carbon * 1.1, min_carbon * 1.1)

        adjusted_params = self.params.copy()
        adjusted_params["carbon_price"] = self.params.get("carbon_price", 0.08) * 5

        result = self._call_solver(adjusted_params, time_limit)

        result["optimization_method"] = "carbon_hierarchical"
        result["min_carbon_achieved"] = min_carbon
        result["carbon_target_met"] = True

        return result

    def calculate_carbon_efficiency(
        self,
        solution: Dict[str, Any],
    ) -> CarbonEfficiencyReport:
        """
        计算碳效率指标。

        Args:
            solution: 求解结果

        Returns:
            CarbonEfficiencyReport 碳效率报告
        """
        cost_data = solution.get("cost_data", {})
        routes = solution.get("routes", [])

        total_carbon = cost_data.get("carbon_emission_kg", 0)
        total_distance = cost_data.get("total_distance_km", 0)

        # 计算客户数量
        total_customers = sum(
            len([s for s in route.get("stops", []) if s.get("node", 0) > 0]) for route in routes
        )

        # 计算总货物量
        total_demand = sum(route.get("total_demand", 0) for route in routes)

        # 单位指标
        carbon_per_km = total_carbon / max(total_distance, 1)
        carbon_per_customer = total_carbon / max(total_customers, 1)
        carbon_per_kg_goods = total_carbon / max(total_demand, 1)

        # 各车型碳效率
        vehicle_efficiency = {}
        for route in routes:
            v_type = route.get("vehicle_type", "unknown")
            distance = route.get("distance_km", 0)
            demand = route.get("total_demand", 0)

            v_config = self.vehicle_config.get(v_type, {})
            fuel_per_100km = v_config.get("fuel_per_100km", 12)

            # 碳排放
            carbon = (distance / 100) * fuel_per_100km * DIESEL_CO2_FACTOR

            # 碳效率：单位货物的碳排放（仅当有货物时计算）
            if demand > 0:
                efficiency = carbon / demand
                if v_type not in vehicle_efficiency:
                    vehicle_efficiency[v_type] = []
                vehicle_efficiency[v_type].append(efficiency)

        # 平均值
        vehicle_efficiency = {k: np.mean(v) for k, v in vehicle_efficiency.items()}

        # 计算减排潜力
        reduction_potential = self._calculate_reduction_potential(solution)

        # 生成建议
        recommendations = self._generate_recommendations(
            solution, vehicle_efficiency, reduction_potential
        )

        return CarbonEfficiencyReport(
            total_carbon_kg=total_carbon,
            carbon_per_km=carbon_per_km,
            carbon_per_customer=carbon_per_customer,
            carbon_per_kg_goods=carbon_per_kg_goods,
            vehicle_efficiency=vehicle_efficiency,
            reduction_potential=reduction_potential,
            recommendations=recommendations,
        )

    def _calculate_reduction_potential(
        self,
        solution: Dict[str, Any],
    ) -> float:
        """
        计算减排潜力。

        通过对比当前解与理论最优解的差距估算。
        """
        routes = solution.get("routes", [])

        # 当前碳排放
        current_carbon = solution.get("cost_data", {}).get("carbon_emission_kg", 0)

        # 理论最优：全部使用单位碳排放最低的车型
        min_carbon_per_capacity = float("inf")
        best_v_type = None

        for v_type, config in self.vehicle_config.items():
            fuel = config.get("fuel_per_100km", 12)
            capacity = config.get("capacity", 1)
            carbon_per_capacity = fuel / capacity

            if carbon_per_capacity < min_carbon_per_capacity:
                min_carbon_per_capacity = carbon_per_capacity
                best_v_type = v_type

        # 估算理论最优碳排放
        total_demand = sum(route.get("total_demand", 0) for route in routes)

        best_config = self.vehicle_config.get(best_v_type, {})
        avg_distance_per_customer = 10  # 假设平均每客户10公里

        theoretical_carbon = (
            (total_demand / best_config.get("capacity", 1))
            * avg_distance_per_customer
            * best_config.get("fuel_per_100km", 12)
            / 100
            * DIESEL_CO2_FACTOR
        )

        # 减排潜力
        potential = max(0, current_carbon - theoretical_carbon)

        return potential

    def _generate_recommendations(
        self,
        solution: Dict[str, Any],
        vehicle_efficiency: Dict[str, float],
        reduction_potential: float,
    ) -> List[str]:
        """
        生成减排建议。
        """
        recommendations = []

        # 车型选择建议
        if vehicle_efficiency:
            best_v_type = min(vehicle_efficiency, key=vehicle_efficiency.get)
            worst_v_type = max(vehicle_efficiency, key=vehicle_efficiency.get)

            if best_v_type != worst_v_type:
                recommendations.append(f"建议优先使用 {best_v_type} 车型，其碳效率最高")

        # 减排潜力提醒
        if reduction_potential > 10:
            recommendations.append(
                f"存在约 {reduction_potential:.1f} kg 的减排潜力，" "可通过优化车型配置实现"
            )

        # 路线优化建议
        routes = solution.get("routes", [])
        empty_rates = []

        for route in routes:
            capacity = route.get("capacity", 1)
            demand = route.get("total_demand", 0)
            empty_rate = 1 - demand / capacity if capacity > 0 else 0
            empty_rates.append(empty_rate)

        if empty_rates and np.mean(empty_rates) > 0.3:
            recommendations.append("车辆空载率较高，建议合并路线或调整车型配置")

        # 时间窗建议
        total_late = solution.get("total_late_minutes", 0)
        if total_late > 0:
            recommendations.append(
                f"存在 {total_late} 分钟迟到，可能导致额外碳排放，" "建议放宽时间窗约束"
            )

        if not recommendations:
            recommendations.append("当前方案碳排放表现良好")

        return recommendations

    def compare_carbon_scenarios(
        self,
        scenarios: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        对比多个场景的碳排放。

        Args:
            scenarios: 场景列表，每个包含 name 和 solution

        Returns:
            对比结果
        """
        comparison = []

        for scenario in scenarios:
            name = scenario.get("name", "未命名")
            solution = scenario.get("solution", {})

            report = self.calculate_carbon_efficiency(solution)

            comparison.append(
                {
                    "scenario": name,
                    "total_carbon_kg": report.total_carbon_kg,
                    "carbon_per_km": report.carbon_per_km,
                    "carbon_per_customer": report.carbon_per_customer,
                }
            )

        # 找出最优场景
        best_scenario = min(comparison, key=lambda x: x["total_carbon_kg"])

        return {
            "comparison": comparison,
            "best_scenario": best_scenario["scenario"],
            "carbon_savings_potential": max(c["total_carbon_kg"] for c in comparison)
            - min(c["total_carbon_kg"] for c in comparison),
        }

    def generate_carbon_report(
        self,
        solution: Dict[str, Any],
        report: Optional[CarbonEfficiencyReport] = None,
    ) -> str:
        """
        生成碳排放文本报告。

        Args:
            solution: 求解结果
            report: 碳效率报告（可选）

        Returns:
            格式化的报告文本
        """
        if report is None:
            report = self.calculate_carbon_efficiency(solution)

        lines = []
        lines.append("=" * 60)
        lines.append("碳排放分析报告")
        lines.append("=" * 60)
        lines.append("")

        # 总量
        lines.append("【碳排放概况】")
        lines.append(f"总碳排放量: {report.total_carbon_kg:.2f} kg CO2")
        lines.append(f"单位距离碳排放: {report.carbon_per_km:.4f} kg/km")
        lines.append(f"单位客户碳排放: {report.carbon_per_customer:.4f} kg/客户")
        lines.append("")

        # 车型分析
        lines.append("【车型碳效率】")
        lines.append("-" * 40)
        for v_type, efficiency in report.vehicle_efficiency.items():
            lines.append(f"{v_type}: {efficiency:.4f} kg/单位货物")
        lines.append("-" * 40)
        lines.append("")

        # 减排建议
        lines.append("【减排建议】")
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")

        lines.append("")

        # 减排潜力
        if report.reduction_potential > 0:
            lines.append(f"【减排潜力】约 {report.reduction_potential:.2f} kg CO2")

        lines.append("=" * 60)

        return "\n".join(lines)
