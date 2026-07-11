"""
策略效果评估模块

评估不同求解策略的效果和稳定性，帮助选择最优策略。
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


@dataclass
class EvaluationResult:
    """策略评估结果数据类。"""

    strategies: List[str]
    """策略名称列表"""

    time_limits: List[int]
    """时间限制列表"""

    results_matrix: Dict[str, List[Dict[str, Any]]]
    """策略 x 时间限制的结果矩阵"""

    performance_metrics: Dict[str, Dict[str, float]]
    """各策略的性能指标"""

    best_strategy: str
    """最优策略"""

    stability_scores: Dict[str, float]
    """各策略的稳定性分数"""

    summary: pd.DataFrame
    """汇总数据表"""

    recommendations: List[str]
    """策略推荐建议"""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "strategies": self.strategies,
            "time_limits": self.time_limits,
            "performance_metrics": self.performance_metrics,
            "best_strategy": self.best_strategy,
            "stability_scores": self.stability_scores,
            "summary": self.summary.to_dict("records"),
            "recommendations": self.recommendations,
        }


# 评估指标配置
EVALUATION_METRICS = {
    "total_cost": {
        "name": "总成本",
        "unit": "元",
        "lower_better": True,
        "weight": 0.4,
    },
    "solve_time": {
        "name": "求解时间",
        "unit": "秒",
        "lower_better": True,
        "weight": 0.2,
    },
    "solution_quality": {
        "name": "解质量",
        "unit": "分",
        "lower_better": False,
        "weight": 0.3,
    },
    "consistency": {
        "name": "稳定性",
        "unit": "分",
        "lower_better": False,
        "weight": 0.1,
    },
}


# 预定义策略配置
DEFAULT_STRATEGIES = {
    "fast": {
        "name": "快速策略",
        "time_limit": 30,
        "strategies": ["PATH_CHEAPEST_ARC"],
        "description": "快速获得可行解，适合实时响应场景",
    },
    "balanced": {
        "name": "均衡策略",
        "time_limit": 60,
        "strategies": ["PATH_CHEAPEST_ARC", "SAVINGS"],
        "description": "平衡求解时间和解质量",
    },
    "thorough": {
        "name": "深度优化",
        "time_limit": 120,
        "strategies": ["PATH_CHEAPEST_ARC", "SAVINGS", "PARALLEL_CHEAPEST_INSERTION"],
        "description": "充分优化，追求最优解",
    },
}


class StrategyEvaluator:
    """策略效果评估器。"""

    def __init__(
        self,
        solver_func,
        customers: List[Dict[str, Any]],
        vehicle_config: Dict[str, Dict[str, Any]],
        params: Dict[str, float],
    ):
        """
        初始化策略评估器。

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

    def evaluate_strategies(
        self,
        strategies: Optional[List[str]] = None,
        time_limits: Optional[List[int]] = None,
        num_runs: int = 3,
        parallel: bool = True,
    ) -> EvaluationResult:
        """
        评估多个策略的效果。

        Args:
            strategies: 策略列表，默认使用预定义策略
            time_limits: 时间限制列表（秒）
            num_runs: 每个配置运行的次数（评估稳定性）
            parallel: 是否并行执行

        Returns:
            EvaluationResult 评估结果
        """
        # 使用默认策略
        if strategies is None:
            strategies = list(DEFAULT_STRATEGIES.keys())

        if time_limits is None:
            time_limits = [30, 60, 120]

        # 执行评估
        results_matrix = self._run_evaluation(strategies, time_limits, num_runs, parallel)

        # 计算性能指标
        performance_metrics = self._calculate_performance_metrics(results_matrix, strategies)

        # 计算稳定性分数
        stability_scores = self._calculate_stability(results_matrix, strategies)

        # 确定最优策略
        best_strategy = self._determine_best_strategy(performance_metrics, stability_scores)

        # 构建汇总表
        summary = self._build_summary_table(strategies, performance_metrics, stability_scores)

        # 生成推荐建议
        recommendations = self._generate_recommendations(
            strategies, performance_metrics, stability_scores
        )

        return EvaluationResult(
            strategies=strategies,
            time_limits=time_limits,
            results_matrix=results_matrix,
            performance_metrics=performance_metrics,
            best_strategy=best_strategy,
            stability_scores=stability_scores,
            summary=summary,
            recommendations=recommendations,
        )

    def _run_evaluation(
        self,
        strategies: List[str],
        time_limits: List[int],
        num_runs: int,
        parallel: bool,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        执行策略评估。
        """
        results_matrix = {}

        for strategy in strategies:
            strategy_results = []
            strategy_config = DEFAULT_STRATEGIES.get(strategy, {})

            for time_limit in time_limits:
                run_results = []

                if parallel:
                    with ThreadPoolExecutor(max_workers=num_runs) as executor:
                        futures = []
                        for run in range(num_runs):
                            future = executor.submit(
                                self._run_single_evaluation,
                                strategy,
                                time_limit,
                                run,
                            )
                            futures.append(future)

                        for future in as_completed(futures):
                            try:
                                result = future.result()
                                run_results.append(result)
                            except Exception as e:
                                print(f"运行失败: {e}")
                else:
                    for run in range(num_runs):
                        try:
                            result = self._run_single_evaluation(strategy, time_limit, run)
                            run_results.append(result)
                        except Exception as e:
                            print(f"运行失败 (策略 {strategy}, 时间 {time_limit}): {e}")

                # 汇总多次运行结果
                if run_results:
                    aggregated = self._aggregate_run_results(run_results)
                    aggregated["time_limit"] = time_limit
                    aggregated["strategy"] = strategy
                    strategy_results.append(aggregated)

            results_matrix[strategy] = strategy_results

        return results_matrix

    def _run_single_evaluation(
        self,
        strategy: str,
        time_limit: int,
        run: int,
    ) -> Dict[str, Any]:
        """
        执行单次评估。
        """
        strategy_config = DEFAULT_STRATEGIES.get(strategy, {})
        solver_strategies = strategy_config.get("strategies", ["PATH_CHEAPEST_ARC"])

        # 修改参数
        eval_params = self.params.copy()
        eval_params["time_limit"] = time_limit

        # 计时
        start_time = time.time()

        # 调用求解器
        result = self.solver_func(
            self.customers,
            self.vehicle_config,
            eval_params,
        )

        solve_time = time.time() - start_time

        result["solve_time"] = solve_time
        result["run"] = run
        result["strategy"] = strategy
        result["time_limit"] = time_limit

        return result

    def _aggregate_run_results(
        self,
        run_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        汇总多次运行结果。
        """
        if not run_results:
            return {}

        # 提取关键指标
        costs = [r.get("cost_data", {}).get("total_cost", 0) for r in run_results]
        solve_times = [r.get("solve_time", 0) for r in run_results]
        distances = [r.get("cost_data", {}).get("total_distance_km", 0) for r in run_results]
        carbons = [r.get("cost_data", {}).get("carbon_emission_kg", 0) for r in run_results]

        # 计算统计量
        aggregated = {
            "mean_cost": np.mean(costs),
            "std_cost": np.std(costs),
            "min_cost": np.min(costs),
            "max_cost": np.max(costs),
            "mean_solve_time": np.mean(solve_times),
            "std_solve_time": np.std(solve_times),
            "mean_distance": np.mean(distances),
            "mean_carbon": np.mean(carbons),
            "num_runs": len(run_results),
        }

        # 保留最优解
        best_idx = np.argmin(costs)
        aggregated["best_solution"] = run_results[best_idx]

        return aggregated

    def _calculate_performance_metrics(
        self,
        results_matrix: Dict[str, List[Dict[str, Any]]],
        strategies: List[str],
    ) -> Dict[str, Dict[str, float]]:
        """
        计算各策略的性能指标。
        """
        metrics = {}

        for strategy in strategies:
            results = results_matrix.get(strategy, [])
            if not results:
                metrics[strategy] = {}
                continue

            # 计算平均值
            mean_costs = [r.get("mean_cost", 0) for r in results]
            mean_times = [r.get("mean_solve_time", 0) for r in results]
            std_costs = [r.get("std_cost", 0) for r in results]

            # 计算解质量分数（相对于最优解）
            best_overall_cost = min(mean_costs) if mean_costs else 0
            quality_scores = []
            for c in mean_costs:
                if best_overall_cost > 0:
                    score = 100 * (1 - (c - best_overall_cost) / best_overall_cost)
                    quality_scores.append(max(0, score))
                else:
                    quality_scores.append(0)

            metrics[strategy] = {
                "mean_cost": np.mean(mean_costs),
                "mean_solve_time": np.mean(mean_times),
                "cost_std": np.mean(std_costs),
                "quality_score": np.mean(quality_scores),
                "best_cost": min(mean_costs),
                "worst_cost": max(mean_costs),
            }

        return metrics

    def _calculate_stability(
        self,
        results_matrix: Dict[str, List[Dict[str, Any]]],
        strategies: List[str],
    ) -> Dict[str, float]:
        """
        计算各策略的稳定性分数。

        稳定性 = 100 - (变异系数 * 100)
        """
        stability = {}

        for strategy in strategies:
            results = results_matrix.get(strategy, [])
            if not results:
                stability[strategy] = 0
                continue

            # 计算变异系数
            mean_costs = [r.get("mean_cost", 0) for r in results]
            std_costs = [r.get("std_cost", 0) for r in results]

            mean_cost = np.mean(mean_costs)
            mean_std = np.mean(std_costs)

            if mean_cost > 0:
                cv = mean_std / mean_cost
                stability[strategy] = max(0, 100 - cv * 100)
            else:
                stability[strategy] = 100

        return stability

    def _determine_best_strategy(
        self,
        performance_metrics: Dict[str, Dict[str, float]],
        stability_scores: Dict[str, float],
    ) -> str:
        """
        确定最优策略。
        """
        scores = {}

        for strategy, metrics in performance_metrics.items():
            if not metrics:
                continue

            # 综合得分
            quality = metrics.get("quality_score", 0)
            speed = 100 - min(100, metrics.get("mean_solve_time", 0))
            stability = stability_scores.get(strategy, 0)

            scores[strategy] = 0.5 * quality + 0.3 * speed + 0.2 * stability

        if not scores:
            return ""

        return max(scores, key=scores.get)

    def _build_summary_table(
        self,
        strategies: List[str],
        performance_metrics: Dict[str, Dict[str, float]],
        stability_scores: Dict[str, float],
    ) -> pd.DataFrame:
        """
        构建汇总表。
        """
        data = []

        for strategy in strategies:
            metrics = performance_metrics.get(strategy, {})
            config = DEFAULT_STRATEGIES.get(strategy, {})

            data.append(
                {
                    "策略": config.get("name", strategy),
                    "平均成本": round(metrics.get("mean_cost", 0), 2),
                    "最优成本": round(metrics.get("best_cost", 0), 2),
                    "平均时间(秒)": round(metrics.get("mean_solve_time", 0), 2),
                    "质量分数": round(metrics.get("quality_score", 0), 1),
                    "稳定性分数": round(stability_scores.get(strategy, 0), 1),
                }
            )

        return pd.DataFrame(data)

    def _generate_recommendations(
        self,
        strategies: List[str],
        performance_metrics: Dict[str, Dict[str, float]],
        stability_scores: Dict[str, float],
    ) -> List[str]:
        """
        生成策略推荐建议。
        """
        recommendations = []

        # 整体推荐
        if self._determine_best_strategy(performance_metrics, stability_scores):
            best = self._determine_best_strategy(performance_metrics, stability_scores)
            config = DEFAULT_STRATEGIES.get(best, {})
            recommendations.append(f"推荐使用 {config.get('name', best)}：综合表现最优")

        # 场景化推荐
        recommendations.append("")

        fast_strategy = None
        thorough_strategy = None

        for strategy in strategies:
            config = DEFAULT_STRATEGIES.get(strategy, {})
            if strategy == "fast":
                fast_strategy = config.get("name", strategy)
            elif strategy == "thorough":
                thorough_strategy = config.get("name", strategy)

        if fast_strategy:
            recommendations.append(f"实时场景推荐 {fast_strategy}：响应速度快")

        if thorough_strategy:
            recommendations.append(f"离线规划推荐 {thorough_strategy}：解质量更高")

        # 稳定性提醒
        low_stability = [s for s in strategies if stability_scores.get(s, 100) < 70]
        if low_stability:
            names = [DEFAULT_STRATEGIES.get(s, {}).get("name", s) for s in low_stability]
            recommendations.append(f"注意：{', '.join(names)} 稳定性较低，建议多次运行取最优")

        return recommendations

    def generate_comparison_chart(
        self,
        result: EvaluationResult,
        metric: str = "total_cost",
        title: Optional[str] = None,
    ) -> go.Figure:
        """
        生成策略对比柱状图。

        Args:
            result: 评估结果
            metric: 对比指标
            title: 图表标题

        Returns:
            Plotly Figure 对象
        """
        if title is None:
            title = "策略效果对比"

        # 准备数据
        strategy_names = []
        values = []
        errors = []
        colors = px.colors.qualitative.Plotly

        for i, strategy in enumerate(result.strategies):
            config = DEFAULT_STRATEGIES.get(strategy, {})
            metrics = result.performance_metrics.get(strategy, {})

            strategy_names.append(config.get("name", strategy))

            if metric == "total_cost":
                values.append(metrics.get("mean_cost", 0))
                errors.append(metrics.get("cost_std", 0))
            elif metric == "solve_time":
                values.append(metrics.get("mean_solve_time", 0))
                errors.append(0)
            else:
                values.append(metrics.get(metric, 0))
                errors.append(0)

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=strategy_names,
                y=values,
                error_y=dict(
                    type="data",
                    array=errors,
                    visible=True,
                ),
                marker_color=colors[: len(strategy_names)],
                text=[f"{v:.1f}" for v in values],
                textposition="outside",
            )
        )

        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            xaxis_title="策略",
            yaxis_title=metric,
            height=400,
            plot_bgcolor="white",
        )

        return fig

    def generate_radar_comparison(
        self, result: EvaluationResult, title: str = "策略综合能力雷达图"
    ) -> go.Figure:
        """
        生成策略综合能力雷达图。

        Args:
            result: 评估结果
            title: 图表标题

        Returns:
            Plotly Figure 对象
        """
        categories = ["解质量", "求解速度", "稳定性"]

        fig = go.Figure()
        colors = px.colors.qualitative.Plotly

        for i, strategy in enumerate(result.strategies):
            metrics = result.performance_metrics.get(strategy, {})

            # 归一化各指标到 0-100
            quality = metrics.get("quality_score", 0)
            speed = 100 - min(100, metrics.get("mean_solve_time", 0))
            stability = result.stability_scores.get(strategy, 0)

            values = [quality, speed, stability]

            fig.add_trace(
                go.Scatterpolar(
                    r=values + [values[0]],
                    theta=categories + [categories[0]],
                    fill="toself",
                    name=DEFAULT_STRATEGIES.get(strategy, {}).get("name", strategy),
                    line_color=colors[i % len(colors)],
                    opacity=0.6,
                )
            )

        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                )
            ),
            showlegend=True,
            height=500,
        )

        return fig

    def generate_time_quality_tradeoff(
        self, result: EvaluationResult, title: str = "求解时间-解质量权衡图"
    ) -> go.Figure:
        """
        生成时间-质量权衡散点图。

        Args:
            result: 评估结果
            title: 图表标题

        Returns:
            Plotly Figure 对象
        """
        fig = go.Figure()
        colors = px.colors.qualitative.Plotly

        for i, strategy in enumerate(result.strategies):
            strategy_results = result.results_matrix.get(strategy, [])

            times = [r.get("mean_solve_time", 0) for r in strategy_results]
            costs = [r.get("mean_cost", 0) for r in strategy_results]

            config = DEFAULT_STRATEGIES.get(strategy, {})

            fig.add_trace(
                go.Scatter(
                    x=times,
                    y=costs,
                    mode="lines+markers",
                    name=config.get("name", strategy),
                    marker=dict(size=10, color=colors[i % len(colors)]),
                    line=dict(width=2),
                )
            )

        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            xaxis_title="求解时间 (秒)",
            yaxis_title="总成本 (元)",
            height=450,
            plot_bgcolor="white",
            showlegend=True,
        )

        return fig

    def generate_stability_chart(
        self, result: EvaluationResult, title: str = "策略稳定性对比"
    ) -> go.Figure:
        """
        生成稳定性对比图。

        Args:
            result: 评估结果
            title: 图表标题

        Returns:
            Plotly Figure 对象
        """
        strategy_names = []
        stability_values = []
        colors = []

        for strategy in result.strategies:
            config = DEFAULT_STRATEGIES.get(strategy, {})
            strategy_names.append(config.get("name", strategy))
            stability = result.stability_scores.get(strategy, 0)
            stability_values.append(stability)

            # 根据稳定性分数着色
            if stability >= 90:
                colors.append("#2ca02c")  # 高稳定性 - 绿色
            elif stability >= 70:
                colors.append("#ffbb33")  # 中等 - 黄色
            else:
                colors.append("#d62728")  # 低稳定性 - 红色

        fig = go.Figure(
            data=[
                go.Bar(
                    x=strategy_names,
                    y=stability_values,
                    marker_color=colors,
                    text=[f"{v:.1f}分" for v in stability_values],
                    textposition="outside",
                )
            ]
        )

        # 添加阈值线
        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color="orange",
            annotation_text="可接受阈值",
        )

        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            xaxis_title="策略",
            yaxis_title="稳定性分数",
            yaxis=dict(range=[0, 105]),
            height=400,
            plot_bgcolor="white",
        )

        return fig

    def generate_evaluation_report(
        self,
        result: EvaluationResult,
    ) -> str:
        """
        生成策略评估报告。

        Args:
            result: 评估结果

        Returns:
            格式化的报告文本
        """
        lines = []
        lines.append("=" * 60)
        lines.append("策略效果评估报告")
        lines.append("=" * 60)
        lines.append("")

        # 最优策略
        best_config = DEFAULT_STRATEGIES.get(result.best_strategy, {})
        lines.append(f"【推荐策略】{best_config.get('name', result.best_strategy)}")
        lines.append("")

        # 性能对比表
        lines.append("【性能对比】")
        lines.append("-" * 60)

        header = f"{'策略':<15} {'平均成本':>12} {'求解时间':>12} {'质量分数':>10} {'稳定性':>10}"
        lines.append(header)
        lines.append("-" * 60)

        for strategy in result.strategies:
            config = DEFAULT_STRATEGIES.get(strategy, {})
            metrics = result.performance_metrics.get(strategy, {})

            row = f"{config.get('name', strategy):<12}"
            row += f"{metrics.get('mean_cost', 0):>12.2f}"
            row += f"{metrics.get('mean_solve_time', 0):>10.1f}秒"
            row += f"{metrics.get('quality_score', 0):>10.1f}"
            row += f"{result.stability_scores.get(strategy, 0):>9.1f}分"
            lines.append(row)

        lines.append("-" * 60)
        lines.append("")

        # 推荐建议
        lines.append("【推荐建议】")
        for rec in result.recommendations:
            lines.append(f"  {rec}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
