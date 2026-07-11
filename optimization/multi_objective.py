"""
多目标优化模块

支持同时优化多个目标（成本、碳排放、时间、服务质量），
生成 Pareto 前沿供决策者权衡选择。
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from exceptions.errors import ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class ObjectiveWeights:
    """目标权重配置。"""

    cost: float = 0.4
    """成本权重"""

    carbon: float = 0.3
    """碳排放权重"""

    time: float = 0.2
    """时间权重"""

    service_level: float = 0.1
    """服务水平权重"""

    def to_list(self) -> List[float]:
        """转换为列表。"""
        return [self.cost, self.carbon, self.time, self.service_level]

    def normalize(self) -> "ObjectiveWeights":
        """归一化权重。"""
        total = self.cost + self.carbon + self.time + self.service_level
        if total == 0:
            return ObjectiveWeights(0.25, 0.25, 0.25, 0.25)
        return ObjectiveWeights(
            cost=self.cost / total,
            carbon=self.carbon / total,
            time=self.time / total,
            service_level=self.service_level / total,
        )

    @classmethod
    def from_dict(cls, d: Dict[str, float]) -> "ObjectiveWeights":
        """从字典创建。"""
        return cls(
            cost=d.get("cost", 0.4),
            carbon=d.get("carbon", 0.3),
            time=d.get("time", 0.2),
            service_level=d.get("service_level", 0.1),
        )


@dataclass
class ParetoFrontResult:
    """Pareto 前沿结果。"""

    solutions: List[Dict[str, Any]]
    """前沿解集合"""

    objective_values: List[Dict[str, float]]
    """各解的目标值"""

    weights_used: List[ObjectiveWeights]
    """使用的权重配置"""

    best_compromise: Dict[str, Any]
    """最佳折中解"""

    knee_point: Optional[int]
    """膝点索引（Pareto前沿上权衡最优的点）"""

    summary: pd.DataFrame
    """汇总表"""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "solutions": self.solutions,
            "objective_values": self.objective_values,
            "weights_used": [w.to_list() for w in self.weights_used],
            "best_compromise": self.best_compromise,
            "knee_point": self.knee_point,
            "summary": self.summary.to_dict("records"),
        }


# 目标配置
OBJECTIVES = {
    "total_cost": {
        "name": "总成本",
        "unit": "元",
        "minimize": True,
    },
    "carbon_emission_kg": {
        "name": "碳排放",
        "unit": "kg",
        "minimize": True,
    },
    "total_time_min": {
        "name": "总时间",
        "unit": "分钟",
        "minimize": True,
    },
    "service_level": {
        "name": "服务水平",
        "unit": "%",
        "minimize": False,  # 最大化
    },
}


class MultiObjectiveOptimizer:
    """多目标优化器。"""

    def __init__(
        self,
        solver_func: Callable,
        customers: List[Dict[str, Any]],
        vehicle_config: Dict[str, Dict[str, Any]],
        params: Dict[str, float],
    ):
        """
        初始化多目标优化器。

        Args:
            solver_func: 求解函数
            customers: 客户数据
            vehicle_config: 车型配置
            params: 全局参数
        """
        self.solver_func = solver_func
        self.customers = customers
        self.vehicle_config = vehicle_config
        self.params = params

    def optimize(
        self,
        weights: Optional[ObjectiveWeights] = None,
        method: str = "weighted_sum",
        time_limit: int = 60,
    ) -> Dict[str, Any]:
        """
        执行多目标优化。

        Args:
            weights: 目标权重
            method: 优化方法
                - "weighted_sum": 加权求和法
                - "epsilon_constraint": ε-约束法
            time_limit: 时间限制

        Returns:
            优化结果
        """
        if weights is None:
            weights = ObjectiveWeights()

        weights = weights.normalize()

        if method == "weighted_sum":
            return self._optimize_weighted_sum(weights, time_limit)
        elif method == "epsilon_constraint":
            return self._optimize_epsilon_constraint(weights, time_limit)
        else:
            raise ConfigurationError(f"未知优化方法: {method}", config_key="method")

    def _optimize_weighted_sum(
        self,
        weights: ObjectiveWeights,
        time_limit: int,
    ) -> Dict[str, Any]:
        """
        加权求和法优化。

        将多目标转化为单目标：
        min w1*f1 + w2*f2 + ...
        """
        # 调整参数以反映权重
        adjusted_params = self.params.copy()

        # 根据权重调整迟到惩罚（影响服务水平）
        base_penalty = self.params.get("late_penalty_per_min", 10)
        adjusted_params["late_penalty_per_min"] = base_penalty * (1 + weights.service_level * 2)

        # 调整碳价权重
        base_carbon = self.params.get("carbon_price", 0.08)
        adjusted_params["carbon_price"] = base_carbon * (1 + weights.carbon * 5)

        # 调整时间权重（通过时薪体现）
        base_wage = self.params.get("hourly_wage", 50)
        adjusted_params["hourly_wage"] = base_wage * (1 + weights.time)

        # 求解
        result = self.solver_func(
            self.customers,
            self.vehicle_config,
            adjusted_params,
        )

        result["optimization_method"] = "weighted_sum"
        result["weights_used"] = weights.to_list()

        return result

    def _optimize_epsilon_constraint(
        self,
        weights: ObjectiveWeights,
        time_limit: int,
    ) -> Dict[str, Any]:
        """
        ε-约束法优化。

        选择一个主目标最小化，其他目标作为约束。
        """
        # 默认以成本为主目标
        # 对碳排放设置约束（通过调整碳价体现）

        adjusted_params = self.params.copy()

        # 设置碳排放约束的影响
        # 高碳价迫使降低碳排放
        carbon_factor = weights.carbon * 10  # 放大效应
        adjusted_params["carbon_price"] = self.params.get("carbon_price", 0.08) * (
            1 + carbon_factor
        )

        result = self.solver_func(
            self.customers,
            self.vehicle_config,
            adjusted_params,
        )

        result["optimization_method"] = "epsilon_constraint"
        result["weights_used"] = weights.to_list()

        return result

    def _solve_pareto_parallel(
        self,
        weight_combinations: List[ObjectiveWeights],
        time_limit_per_point: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, float]]]:
        """并行求解所有权重组合。"""
        solutions: List[Dict[str, Any]] = []
        objective_values: List[Dict[str, float]] = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(
                    self._solve_with_weights, weights, time_limit_per_point
                ): weights
                for weights in weight_combinations
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result.get("solution_status") == "SUCCESS":
                        solutions.append(result)
                        objective_values.append(self._extract_objectives(result))
                except Exception as e:
                    logger.error("Pareto 并行求解失败: %s", str(e)[:200])

        return solutions, objective_values

    def _solve_pareto_serial(
        self,
        weight_combinations: List[ObjectiveWeights],
        time_limit_per_point: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, float]]]:
        """串行求解所有权重组合。"""
        solutions: List[Dict[str, Any]] = []
        objective_values: List[Dict[str, float]] = []

        for weights in weight_combinations:
            try:
                result = self._solve_with_weights(weights, time_limit_per_point)
                if result.get("solution_status") == "SUCCESS":
                    solutions.append(result)
                    objective_values.append(self._extract_objectives(result))
            except Exception as e:
                logger.error("Pareto 串行求解失败: %s", str(e)[:200])

        return solutions, objective_values

    def generate_pareto_front(
        self,
        num_points: int = 20,
        time_limit_per_point: int = 30,
        parallel: bool = True,
    ) -> ParetoFrontResult:
        """
        生成 Pareto 前沿。

        通过变化权重生成多个非支配解。

        Args:
            num_points: 生成点数量
            time_limit_per_point: 每点的时间限制
            parallel: 是否并行执行

        Returns:
            ParetoFrontResult 结果
        """
        # 生成权重组合
        weight_combinations = self._generate_weight_grid(num_points)

        # 求解所有权重组合
        if parallel:
            solutions, objective_values = self._solve_pareto_parallel(
                weight_combinations, time_limit_per_point,
            )
        else:
            solutions, objective_values = self._solve_pareto_serial(
                weight_combinations, time_limit_per_point,
            )

        if not solutions:
            return self._create_empty_pareto_result()

        # 过滤非支配解
        pareto_indices = self._filter_pareto_front(objective_values)

        pareto_solutions = [solutions[i] for i in pareto_indices]
        pareto_objectives = [objective_values[i] for i in pareto_indices]
        pareto_weights = [weight_combinations[i] for i in pareto_indices]

        # 找到最佳折中解
        best_idx = self._find_best_compromise(pareto_objectives)
        best_compromise = pareto_solutions[best_idx] if pareto_solutions else {}

        # 找到膝点
        knee_point = self._find_knee_point(pareto_objectives)

        # 构建汇总表
        summary = self._build_summary_table(pareto_solutions, pareto_objectives, pareto_weights)

        return ParetoFrontResult(
            solutions=pareto_solutions,
            objective_values=pareto_objectives,
            weights_used=pareto_weights,
            best_compromise=best_compromise,
            knee_point=knee_point,
            summary=summary,
        )

    def _generate_weight_grid(
        self,
        num_points: int,
    ) -> List[ObjectiveWeights]:
        """
        生成权重网格。

        使用简单随机采样生成权重组合。
        """
        weights_list = []
        # 修复：使用局部随机生成器避免全局污染
        rng = np.random.default_rng(42)

        for _ in range(num_points):
            # 随机生成权重
            raw_weights = rng.dirichlet([1, 1, 1, 1])
            weights = ObjectiveWeights(
                cost=raw_weights[0],
                carbon=raw_weights[1],
                time=raw_weights[2],
                service_level=raw_weights[3],
            )
            weights_list.append(weights)

        return weights_list

    def _solve_with_weights(
        self,
        weights: ObjectiveWeights,
        time_limit: int,
    ) -> Dict[str, Any]:
        """
        使用指定权重求解。
        """
        return self.optimize(weights, time_limit=time_limit)

    def _extract_objectives(
        self,
        solution: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        提取目标值。
        """
        cost_data = solution.get("cost_data", {})

        # 计算服务水平（按时送达比例）
        total_late = solution.get("total_late_minutes", 0)
        total_customers = sum(
            len(route.get("stops", [])) - 2 for route in solution.get("routes", [])  # 减去起终点
        )
        service_level = max(0, 100 - (total_late / max(total_customers, 1) * 10))

        return {
            "total_cost": cost_data.get("total_cost", 0),
            "carbon_emission_kg": cost_data.get("carbon_emission_kg", 0),
            "total_time_min": cost_data.get("total_time_min", 0),
            "service_level": service_level,
        }

    def _filter_pareto_front(
        self,
        objective_values: List[Dict[str, float]],
    ) -> List[int]:
        """
        过滤非支配解（v3优化版 - 使用分块和NumPy向量化）。

        对于最小化目标，解 i 支配解 j 当且仅当：
        i 的所有目标都不比 j 差，且至少有一个更好。

        优化策略：
        1. 使用NumPy数组存储目标值，支持向量化比较
        2. 分块处理，利用缓存局部性
        3. 提前终止：一旦发现被支配立即跳过
        """
        n = len(objective_values)
        if n <= 1:
            return list(range(n))

        # 转换为NumPy数组以加速比较
        obj_names = list(OBJECTIVES.keys())
        obj_matrix = np.zeros((n, len(obj_names)))

        for i, obj_val in enumerate(objective_values):
            for j, name in enumerate(obj_names):
                obj_matrix[i, j] = obj_val.get(name, 0)

        # 标记是否为最小化目标
        minimize_mask = np.array([OBJECTIVES[name]["minimize"] for name in obj_names])

        is_dominated = np.zeros(n, dtype=bool)

        # 分块大小（根据CPU缓存大小调整）
        BLOCK_SIZE = 64

        for block_start in range(0, n, BLOCK_SIZE):
            block_end = min(block_start + BLOCK_SIZE, n)
            block_indices = range(block_start, block_end)

            for i in block_indices:
                if is_dominated[i]:
                    continue

                # 向量化比较：检查i是否被任何其他解支配
                # 条件：所有目标都不比i差，且至少一个更好
                not_worse = np.all(
                    np.where(
                        minimize_mask, obj_matrix <= obj_matrix[i], obj_matrix >= obj_matrix[i]
                    ),
                    axis=1,
                )
                strictly_better = np.any(
                    np.where(minimize_mask, obj_matrix < obj_matrix[i], obj_matrix > obj_matrix[i]),
                    axis=1,
                )

                dominates_i = not_worse & strictly_better
                # 排除i自身
                dominates_i[i] = False

                if np.any(dominates_i):
                    is_dominated[i] = True

        return [i for i in range(n) if not is_dominated[i]]

    def _dominates(
        self,
        sol1: Dict[str, float],
        sol2: Dict[str, float],
    ) -> bool:
        """
        检查 sol1 是否支配 sol2。
        """
        at_least_one_better = False

        for obj_name, obj_config in OBJECTIVES.items():
            v1 = sol1.get(obj_name, 0)
            v2 = sol2.get(obj_name, 0)

            minimize = obj_config["minimize"]

            if minimize:
                if v1 > v2:
                    return False
                if v1 < v2:
                    at_least_one_better = True
            else:
                if v1 < v2:
                    return False
                if v1 > v2:
                    at_least_one_better = True

        return at_least_one_better

    def _find_best_compromise(
        self,
        objective_values: List[Dict[str, float]],
    ) -> int:
        """
        找到最佳折中解。

        使用理想点法：选择距离理想点最近的解。
        """
        if not objective_values:
            return 0

        # 找到理想点（每个目标的最优值）
        ideal = {}
        for obj_name, obj_config in OBJECTIVES.items():
            values = [v.get(obj_name, 0) for v in objective_values]
            if obj_config["minimize"]:
                ideal[obj_name] = min(values)
            else:
                ideal[obj_name] = max(values)

        # 计算每个解到理想点的距离
        min_distance = float("inf")
        best_idx = 0

        for i, obj_val in enumerate(objective_values):
            distance = 0
            for obj_name, obj_config in OBJECTIVES.items():
                v = obj_val.get(obj_name, 0)
                ideal_v = ideal[obj_name]
                range_v = max(abs(v - ideal_v), 1)

                # 归一化距离
                if obj_config["minimize"]:
                    distance += ((v - ideal_v) / range_v) ** 2
                else:
                    distance += ((ideal_v - v) / range_v) ** 2

            distance = distance**0.5

            if distance < min_distance:
                min_distance = distance
                best_idx = i

        return best_idx

    def _find_knee_point(
        self,
        objective_values: List[Dict[str, float]],
    ) -> Optional[int]:
        """
        找到膝点（Pareto 前沿上权衡最优的点）。

        膝点是目标值改善的边际收益最大变化的点。
        """
        if len(objective_values) < 3:
            return 0

        # 基于成本-碳排放权衡找膝点
        costs = [v.get("total_cost", 0) for v in objective_values]
        carbons = [v.get("carbon_emission_kg", 0) for v in objective_values]

        # 按成本排序
        sorted_indices = np.argsort(costs)
        sorted_costs = [costs[i] for i in sorted_indices]
        sorted_carbons = [carbons[i] for i in sorted_indices]

        # 计算斜率变化
        max_knee_score = 0
        knee_idx = 0

        for i in range(1, len(sorted_indices) - 1):
            # 计算前后斜率
            slope_before = (sorted_carbons[i] - sorted_carbons[i - 1]) / max(
                sorted_costs[i] - sorted_costs[i - 1], 1
            )
            slope_after = (sorted_carbons[i + 1] - sorted_carbons[i]) / max(
                sorted_costs[i + 1] - sorted_costs[i], 1
            )

            # 斜率变化大的点是膝点
            knee_score = abs(slope_after - slope_before)

            if knee_score > max_knee_score:
                max_knee_score = knee_score
                knee_idx = sorted_indices[i]

        return knee_idx

    def _build_summary_table(
        self,
        solutions: List[Dict[str, Any]],
        objective_values: List[Dict[str, float]],
        weights: List[ObjectiveWeights],
    ) -> pd.DataFrame:
        """
        构建汇总表。
        """
        data = []

        for i, (sol, obj, w) in enumerate(zip(solutions, objective_values, weights)):
            data.append(
                {
                    "解编号": i + 1,
                    "总成本(元)": round(obj.get("total_cost", 0), 2),
                    "碳排放(kg)": round(obj.get("carbon_emission_kg", 0), 2),
                    "总时间(分)": round(obj.get("total_time_min", 0), 1),
                    "服务水平(%)": round(obj.get("service_level", 0), 1),
                    "成本权重": round(w.cost, 2),
                    "碳排权重": round(w.carbon, 2),
                }
            )

        return pd.DataFrame(data)

    def _create_empty_pareto_result(self) -> ParetoFrontResult:
        """创建空的 Pareto 结果。"""
        return ParetoFrontResult(
            solutions=[],
            objective_values=[],
            weights_used=[],
            best_compromise={},
            knee_point=None,
            summary=pd.DataFrame(),
        )

    def calculate_tradeoffs(
        self,
        pareto_result: ParetoFrontResult,
    ) -> List[Dict[str, Any]]:
        """
        计算权衡分析。

        分析不同目标之间的边际替代率。
        """
        if len(pareto_result.solutions) < 2:
            return []

        tradeoffs = []
        obj_values = pareto_result.objective_values

        for i in range(len(obj_values) - 1):
            for j in range(i + 1, len(obj_values)):
                cost_diff = obj_values[j].get("total_cost", 0) - obj_values[i].get("total_cost", 0)
                carbon_diff = obj_values[j].get("carbon_emission_kg", 0) - obj_values[i].get(
                    "carbon_emission_kg", 0
                )

                if cost_diff != 0 and carbon_diff != 0:
                    # 边际碳减排成本
                    marginal_cost = abs(carbon_diff / cost_diff)

                    tradeoffs.append(
                        {
                            "solution_pair": (i + 1, j + 1),
                            "cost_change": round(cost_diff, 2),
                            "carbon_change": round(carbon_diff, 2),
                            "marginal_carbon_cost": round(marginal_cost, 4),
                        }
                    )

        return tradeoffs
