"""
多场景对比分析模块

支持对比多个场景或多个求解结果的成本、碳排放、距离、车辆数等关键指标。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


@dataclass
class ComparisonResult:
    """场景对比结果数据类。"""

    scenarios: List[str]
    """场景名称列表"""

    metrics: Dict[str, List[float]]
    """各指标的值列表，key为指标名，value为各场景的值"""

    rankings: Dict[str, List[int]]
    """各指标的排名，1为最优"""

    best_scenario: str
    """综合最优场景"""

    summary: pd.DataFrame
    """汇总数据表"""

    tradeoffs: List[Dict[str, Any]] = field(default_factory=list)
    """权衡分析结果"""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "scenarios": self.scenarios,
            "metrics": self.metrics,
            "rankings": self.rankings,
            "best_scenario": self.best_scenario,
            "summary": self.summary.to_dict("records"),
            "tradeoffs": self.tradeoffs,
        }


# 对比指标配置
COMPARISON_METRICS = {
    "total_cost": {
        "name": "总成本",
        "unit": "元",
        "lower_better": True,
        "weight": 0.35,
    },
    "carbon_emission_kg": {
        "name": "碳排放量",
        "unit": "kg CO2",
        "lower_better": True,
        "weight": 0.25,
    },
    "total_distance_km": {
        "name": "总距离",
        "unit": "km",
        "lower_better": True,
        "weight": 0.20,
    },
    "vehicle_count": {
        "name": "车辆数",
        "unit": "辆",
        "lower_better": True,
        "weight": 0.15,
    },
    "total_time_min": {
        "name": "总时间",
        "unit": "分钟",
        "lower_better": True,
        "weight": 0.05,
    },
}


class ScenarioComparison:
    """多场景对比分析器。"""

    def __init__(
        self,
        metric_weights: Optional[Dict[str, float]] = None,
    ):
        """
        初始化对比分析器。

        Args:
            metric_weights: 指标权重配置，默认使用 COMPARISON_METRICS
        """
        self.metric_weights = metric_weights or {
            k: v["weight"] for k, v in COMPARISON_METRICS.items()
        }
        self.metrics_config = COMPARISON_METRICS

    def compare_solutions(
        self,
        solutions: List[Dict[str, Any]],
        scenario_names: Optional[List[str]] = None,
    ) -> ComparisonResult:
        """
        对比多个求解结果。

        Args:
            solutions: 求解结果列表，每个包含 cost_data 和 solution_data
            scenario_names: 场景名称列表，默认为 ["场景1", "场景2", ...]

        Returns:
            ComparisonResult 对比结果
        """
        # 生成场景名称
        if scenario_names is None:
            scenario_names = [f"场景{i+1}" for i in range(len(solutions))]

        # 提取指标数据
        metrics_data = {metric: [] for metric in COMPARISON_METRICS}

        for solution in solutions:
            cost_data = solution.get("cost_data", {})
            solution_data = solution.get("solution_data", solution)

            metrics_data["total_cost"].append(cost_data.get("total_cost", 0))
            metrics_data["carbon_emission_kg"].append(cost_data.get("carbon_emission_kg", 0))
            metrics_data["total_distance_km"].append(
                cost_data.get("total_distance_km", solution_data.get("total_distance", 0))
            )

            # 计算车辆数
            vehicles_used = solution_data.get("vehicles_used", {})
            vehicle_count = sum(vehicles_used.values()) if vehicles_used else 0
            metrics_data["vehicle_count"].append(vehicle_count)

            metrics_data["total_time_min"].append(cost_data.get("total_time_min", 0))

        # 计算排名
        rankings = {}
        for metric, values in metrics_data.items():
            config = COMPARISON_METRICS.get(metric, {})
            lower_better = config.get("lower_better", True)

            # 排序获取排名
            sorted_indices = np.argsort(values)
            if not lower_better:
                sorted_indices = sorted_indices[::-1]

            ranks = [0] * len(values)
            for rank, idx in enumerate(sorted_indices, 1):
                ranks[idx] = rank
            rankings[metric] = ranks

        # 计算综合得分
        scores = self._calculate_composite_scores(metrics_data)
        best_idx = np.argmax(scores)
        best_scenario = scenario_names[best_idx]

        # 构建汇总表
        summary_data = {
            "场景": scenario_names,
            "综合得分": [round(s, 3) for s in scores],
        }
        for metric, values in metrics_data.items():
            config = COMPARISON_METRICS.get(metric, {})
            name = config.get("name", metric)
            unit = config.get("unit", "")
            summary_data[f"{name}({unit})"] = [round(v, 2) for v in values]

        summary_df = pd.DataFrame(summary_data)

        # 分析权衡关系
        tradeoffs = self._analyze_tradeoffs(metrics_data, scenario_names)

        return ComparisonResult(
            scenarios=scenario_names,
            metrics=metrics_data,
            rankings=rankings,
            best_scenario=best_scenario,
            summary=summary_df,
            tradeoffs=tradeoffs,
        )

    def _calculate_composite_scores(self, metrics_data: Dict[str, List[float]]) -> List[float]:
        """
        计算综合得分（加权归一化）。

        使用 Min-Max 归一化后加权求和。
        """
        num_scenarios = len(next(iter(metrics_data.values())))
        scores = [0.0] * num_scenarios

        for metric, values in metrics_data.items():
            config = COMPARISON_METRICS.get(metric, {})
            weight = self.metric_weights.get(metric, 0.1)
            lower_better = config.get("lower_better", True)

            # 归一化
            min_val = min(values) if values else 0
            max_val = max(values) if values else 1
            range_val = max_val - min_val if max_val != min_val else 1

            for i, val in enumerate(values):
                normalized = (val - min_val) / range_val
                if lower_better:
                    normalized = 1 - normalized
                scores[i] += normalized * weight

        return scores

    def _analyze_tradeoffs(
        self,
        metrics_data: Dict[str, List[float]],
        scenario_names: List[str],
    ) -> List[Dict[str, Any]]:
        """
        分析场景间的权衡关系。

        识别哪些场景在哪些指标上表现更好。
        """
        tradeoffs = []

        if len(scenario_names) < 2:
            return tradeoffs

        # 找出每个指标的最优场景
        for metric, values in metrics_data.items():
            config = COMPARISON_METRICS.get(metric, {})
            lower_better = config.get("lower_better", True)

            best_idx = np.argmin(values) if lower_better else np.argmax(values)
            worst_idx = np.argmax(values) if lower_better else np.argmin(values)

            tradeoffs.append(
                {
                    "metric": config.get("name", metric),
                    "best_scenario": scenario_names[best_idx],
                    "best_value": round(values[best_idx], 2),
                    "worst_scenario": scenario_names[worst_idx],
                    "worst_value": round(values[worst_idx], 2),
                    "improvement_potential": round(abs(values[worst_idx] - values[best_idx]), 2),
                }
            )

        return tradeoffs

    def generate_radar_chart(
        self, result: ComparisonResult, title: str = "多场景指标雷达图"
    ) -> go.Figure:
        """
        生成雷达图对比多场景。

        Args:
            result: 对比结果
            title: 图表标题

        Returns:
            Plotly Figure 对象
        """
        categories = [COMPARISON_METRICS[m]["name"] for m in COMPARISON_METRICS]

        fig = go.Figure()

        # 颜色配置
        colors = px.colors.qualitative.Plotly

        for i, scenario in enumerate(result.scenarios):
            # 归一化各指标值（0-100分制）
            values = []
            for metric in COMPARISON_METRICS:
                metric_values = result.metrics[metric]
                config = COMPARISON_METRICS[metric]
                val = metric_values[i]

                # 归一化到0-100
                min_v = min(metric_values)
                max_v = max(metric_values)
                if max_v == min_v:
                    normalized = 50
                else:
                    normalized = (val - min_v) / (max_v - min_v) * 100
                    if config["lower_better"]:
                        normalized = 100 - normalized

                values.append(round(normalized, 1))

            # 闭合雷达图
            values.append(values[0])

            fig.add_trace(
                go.Scatterpolar(
                    r=values,
                    theta=categories + [categories[0]],
                    fill="toself",
                    name=scenario,
                    line_color=colors[i % len(colors)],
                    opacity=0.6,
                )
            )

        fig.update_layout(
            title=dict(text=title, font=dict(size=18)),
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                )
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
            ),
            height=500,
        )

        return fig

    def generate_bar_comparison(
        self,
        result: ComparisonResult,
        metric: str = "total_cost",
        title: Optional[str] = None,
    ) -> go.Figure:
        """
        生成柱状图对比单个指标。

        Args:
            result: 对比结果
            metric: 要对比的指标
            title: 图表标题

        Returns:
            Plotly Figure 对象
        """
        config = COMPARISON_METRICS.get(metric, {})
        metric_name = config.get("name", metric)
        unit = config.get("unit", "")

        if title is None:
            title = f"各场景{metric_name}对比"

        values = result.metrics.get(metric, [])

        # 颜色根据排名
        rankings = result.rankings.get(metric, [])
        colors = []
        for rank in rankings:
            if rank == 1:
                colors.append("#2ca02c")  # 最优 - 绿色
            elif rank == 2:
                colors.append("#1f77b4")  # 次优 - 蓝色
            else:
                colors.append("#ff7f0e")  # 其他 - 橙色

        fig = go.Figure(
            data=[
                go.Bar(
                    x=result.scenarios,
                    y=values,
                    marker_color=colors,
                    text=[f"{v:,.1f} {unit}" for v in values],
                    textposition="outside",
                )
            ]
        )

        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            xaxis_title="场景",
            yaxis_title=f"{metric_name} ({unit})",
            height=400,
            plot_bgcolor="white",
            margin=dict(t=80),
        )

        return fig

    def generate_heatmap(
        self, result: ComparisonResult, title: str = "场景排名热力图"
    ) -> go.Figure:
        """
        生成排名热力图。

        Args:
            result: 对比结果
            title: 图表标题

        Returns:
            Plotly Figure 对象
        """
        # 构建排名矩阵
        metrics_names = [COMPARISON_METRICS[m]["name"] for m in COMPARISON_METRICS]

        ranking_matrix = []
        for metric in COMPARISON_METRICS:
            ranking_matrix.append(result.rankings.get(metric, []))

        fig = go.Figure(
            data=go.Heatmap(
                z=ranking_matrix,
                x=result.scenarios,
                y=metrics_names,
                colorscale=[
                    [0, "#2ca02c"],  # 排名1 - 绿色
                    [0.5, "#ffbb33"],  # 中间 - 黄色
                    [1, "#d62728"],  # 排名靠后 - 红色
                ],
                colorbar=dict(title="排名"),
                text=[[str(r) for r in row] for row in ranking_matrix],
                texttemplate="%{text}",
                textfont={"size": 14},
            )
        )

        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            xaxis_title="场景",
            yaxis_title="指标",
            height=350,
        )

        return fig

    def generate_comparison_report(
        self,
        result: ComparisonResult,
    ) -> str:
        """
        生成文本对比报告。

        Args:
            result: 对比结果

        Returns:
            格式化的报告文本
        """
        lines = []
        lines.append("=" * 60)
        lines.append("多场景对比分析报告")
        lines.append("=" * 60)
        lines.append("")

        # 最优场景
        lines.append(f"【综合最优场景】{result.best_scenario}")
        lines.append("")

        # 指标对比表
        lines.append("【指标对比】")
        lines.append("-" * 60)

        header = f"{'指标':<15}"
        for name in result.scenarios:
            header += f"{name:<15}"
        lines.append(header)
        lines.append("-" * 60)

        for metric, values in result.metrics.items():
            config = COMPARISON_METRICS.get(metric, {})
            name = config.get("name", metric)
            unit = config.get("unit", "")
            row_name = f"{name}({unit})"
            row = f"{row_name:<12}"
            for val in values:
                row += f"{val:>12.2f}  "
            lines.append(row)

        lines.append("-" * 60)
        lines.append("")

        # 权衡分析
        if result.tradeoffs:
            lines.append("【权衡分析】")
            lines.append("-" * 60)
            for t in result.tradeoffs:
                lines.append(
                    f"{t['metric']}: {t['best_scenario']} 最优 ({t['best_value']}), "
                    f"{t['worst_scenario']} 最差 ({t['worst_value']}), "
                    f"改进空间 {t['improvement_potential']}"
                )

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
