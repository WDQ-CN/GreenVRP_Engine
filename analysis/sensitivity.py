"""
参数敏感度分析模块

分析模型参数变化对求解结果的影响，帮助决策者理解参数的重要性。
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# 使用统一的日志系统
logger = logging.getLogger(__name__)


@dataclass
class SensitivityResult:
    """敏感度分析结果数据类。"""

    parameter_name: str
    """参数名称"""

    base_value: float
    """基准值"""

    test_values: List[float]
    """测试值列表"""

    results: List[Dict[str, Any]]
    """各测试值的求解结果"""

    sensitivities: Dict[str, float]
    """各指标对参数的敏感度系数"""

    impact_ranking: List[Tuple[str, float]]
    """影响程度排序 [(指标名, 敏感度)]"""

    summary: pd.DataFrame
    """汇总数据表"""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "parameter_name": self.parameter_name,
            "base_value": self.base_value,
            "test_values": self.test_values,
            "results": self.results,
            "sensitivities": self.sensitivities,
            "impact_ranking": self.impact_ranking,
            "summary": self.summary.to_dict("records"),
        }


# 敏感度指标配置
SENSITIVITY_METRICS = {
    "total_cost": {"name": "总成本", "unit": "元"},
    "carbon_emission_kg": {"name": "碳排放量", "unit": "kg"},
    "total_distance_km": {"name": "总距离", "unit": "km"},
    "vehicle_count": {"name": "车辆数", "unit": "辆"},
}


# 可分析的参数配置
ANALYZABLE_PARAMETERS = {
    "fuel_price": {
        "name": "油价",
        "unit": "元/升",
        "range": (6.0, 9.0),
        "default_step": 0.5,
    },
    "hourly_wage": {
        "name": "时薪",
        "unit": "元/小时",
        "range": (30.0, 80.0),
        "default_step": 5.0,
    },
    "carbon_price": {
        "name": "碳价",
        "unit": "元/kg",
        "range": (0.0, 0.3),
        "default_step": 0.05,
    },
    "late_penalty_per_min": {
        "name": "迟到罚金",
        "unit": "元/分钟",
        "range": (5.0, 20.0),
        "default_step": 2.5,
    },
    "vehicle_fixed_cost_factor": {
        "name": "固定成本系数",
        "unit": "倍",
        "range": (0.5, 2.0),
        "default_step": 0.25,
    },
    "vehicle_capacity_factor": {
        "name": "容量系数",
        "unit": "倍",
        "range": (0.8, 1.5),
        "default_step": 0.1,
    },
}


class SensitivityAnalyzer:
    """参数敏感度分析器。"""

    def __init__(
        self,
        solver_func: Callable,
        base_params: Dict[str, float],
        base_vehicle_config: Dict[str, Dict[str, Any]],
        base_customers: List[Dict[str, Any]],
    ):
        """
        初始化敏感度分析器。

        Args:
            solver_func: 求解函数，接受 (customers, vehicle_config, params) 参数
            base_params: 基准参数配置
            base_vehicle_config: 基准车型配置
            base_customers: 基准客户数据
        """
        self.solver_func = solver_func
        self.base_params = base_params.copy()
        self.base_vehicle_config = base_vehicle_config.copy()
        self.base_customers = base_customers.copy()

    def analyze_parameter(
        self,
        parameter: str,
        values: Optional[List[float]] = None,
        num_points: int = 7,
        parallel: bool = True,
    ) -> SensitivityResult:
        """
        分析单个参数的敏感度。

        Args:
            parameter: 参数名称
            values: 测试值列表，默认根据参数范围自动生成
            num_points: 测试点数量
            parallel: 是否并行执行

        Returns:
            SensitivityResult 分析结果
        """
        if parameter not in ANALYZABLE_PARAMETERS:
            raise ValueError(f"未知参数: {parameter}")

        param_config = ANALYZABLE_PARAMETERS[parameter]
        base_value = self.base_params.get(parameter, 0)

        # 生成测试值
        if values is None:
            range_min, range_max = param_config["range"]
            values = np.linspace(range_min, range_max, num_points).tolist()

        # 求解各参数值
        results = self._run_sensitivity_analysis(parameter, values, parallel)

        # 计算敏感度系数
        sensitivities = self._calculate_sensitivities(results, values, base_value)

        # 影响程度排序
        impact_ranking = sorted(sensitivities.items(), key=lambda x: abs(x[1]), reverse=True)

        # 构建汇总表
        summary_data = {
            param_config["name"]: [round(v, 2) for v in values],
        }

        for metric, config in SENSITIVITY_METRICS.items():
            metric_values = [r.get("cost_data", {}).get(metric, 0) for r in results]
            summary_data[config["name"]] = [round(v, 2) for v in metric_values]

        summary_df = pd.DataFrame(summary_data)

        return SensitivityResult(
            parameter_name=parameter,
            base_value=base_value,
            test_values=values,
            results=results,
            sensitivities=sensitivities,
            impact_ranking=impact_ranking,
            summary=summary_df,
        )

    def _run_sensitivity_analysis(
        self,
        parameter: str,
        values: List[float],
        parallel: bool,
    ) -> List[Dict[str, Any]]:
        """
        执行敏感度分析求解。
        """
        results = []

        if parallel:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {}
                for val in values:
                    future = executor.submit(self._solve_with_param, parameter, val)
                    futures[future] = val

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.warning(f"求解失败: {e}")
                        results.append({})

            # 按原始顺序排序
            results_dict = {r.get("_param_value", 0): r for r in results if r}
            results = [results_dict.get(v, {}) for v in values]
        else:
            for val in values:
                try:
                    result = self._solve_with_param(parameter, val)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"求解失败 (参数值 {val}): {e}")
                    results.append({})

        return results

    def _solve_with_param(
        self,
        parameter: str,
        value: float,
    ) -> Dict[str, Any]:
        """
        使用指定参数值求解。
        """
        # 修改参数
        params = self.base_params.copy()
        params[parameter] = value

        # 特殊处理容量系数（使用浅拷贝 + 字典推导式避免深拷贝）
        # vehicle_config 是嵌套字典，需要复制每一层
        vehicle_config = {
            v_type: config.copy() 
            for v_type, config in self.base_vehicle_config.items()
        }
        if parameter == "vehicle_capacity_factor":
            for v_type in vehicle_config:
                base_capacity = self.base_vehicle_config[v_type].get("capacity", 100)
                vehicle_config[v_type]["capacity"] = int(base_capacity * value)

        # 特殊处理固定成本系数
        if parameter == "vehicle_fixed_cost_factor":
            for v_type in vehicle_config:
                base_fixed = self.base_vehicle_config[v_type].get("fixed_cost", 100)
                vehicle_config[v_type]["fixed_cost"] = base_fixed * value

        # 调用求解器
        result = self.solver_func(
            self.base_customers,
            vehicle_config,
            params,
        )

        result["_param_value"] = value
        return result

    def _calculate_sensitivities(
        self,
        results: List[Dict[str, Any]],
        values: List[float],
        base_value: float,
    ) -> Dict[str, float]:
        """
        计算各指标的敏感度系数。

        敏感度 = (Δ指标/指标基准) / (Δ参数/参数基准)
        """
        sensitivities = {}

        # 找到基准值对应的结果
        base_idx = None
        for i, v in enumerate(values):
            if abs(v - base_value) < 0.001:
                base_idx = i
                break

        if base_idx is None or base_idx >= len(results):
            return sensitivities

        base_result = results[base_idx]

        for metric in SENSITIVITY_METRICS:
            base_metric = base_result.get("cost_data", {}).get(metric, 0)
            if base_metric == 0:
                sensitivities[metric] = 0
                continue

            # 使用线性回归计算敏感度
            metric_values = [r.get("cost_data", {}).get(metric, 0) for r in results]

            # 相对变化
            relative_param_changes = [
                (v - base_value) / base_value if base_value != 0 else 0 for v in values
            ]
            relative_metric_changes = [
                (m - base_metric) / base_metric if base_metric != 0 else 0 for m in metric_values
            ]

            # 线性回归计算斜率
            if len(values) > 1:
                x = np.array(relative_param_changes)
                y = np.array(relative_metric_changes)

                # 最小二乘
                n = len(x)
                sum_x = np.sum(x)
                sum_y = np.sum(y)
                sum_xy = np.sum(x * y)
                sum_x2 = np.sum(x**2)

                denominator = n * sum_x2 - sum_x**2
                if abs(denominator) > 1e-10:
                    slope = (n * sum_xy - sum_x * sum_y) / denominator
                    sensitivities[metric] = round(slope, 4)
                else:
                    sensitivities[metric] = 0
            else:
                sensitivities[metric] = 0

        return sensitivities

    def analyze_multiple_parameters(
        self,
        parameters: Optional[List[str]] = None,
        num_points: int = 5,
        parallel: bool = True,
    ) -> Dict[str, SensitivityResult]:
        """
        分析多个参数的敏感度。

        Args:
            parameters: 参数列表，默认分析所有可分析参数
            num_points: 每个参数的测试点数量
            parallel: 是否并行执行

        Returns:
            参数名到分析结果的映射
        """
        if parameters is None:
            parameters = list(ANALYZABLE_PARAMETERS.keys())

        results = {}
        for param in parameters:
            try:
                result = self.analyze_parameter(param, num_points=num_points, parallel=parallel)
                results[param] = result
            except Exception as e:
                logger.warning(f"分析参数 {param} 失败: {e}")

        return results

    def generate_tornado_chart(
        self,
        results: Dict[str, SensitivityResult],
        metric: str = "total_cost",
        title: Optional[str] = None,
    ) -> go.Figure:
        """
        生成龙卷风图展示参数敏感度。

        Args:
            results: 多参数分析结果
            metric: 要展示的指标
            title: 图表标题

        Returns:
            Plotly Figure 对象
        """
        if title is None:
            title = f"{SENSITIVITY_METRICS[metric]['name']}敏感度分析"

        # 收集各参数的影响范围
        param_impacts = []
        for param, result in results.items():
            metric_values = [r.get("cost_data", {}).get(metric, 0) for r in result.results]

            if not metric_values:
                continue

            base_value = result.base_value
            min_change = min(metric_values) - base_value
            max_change = max(metric_values) - base_value

            param_config = ANALYZABLE_PARAMETERS.get(param, {})
            param_impacts.append(
                {
                    "parameter": param_config.get("name", param),
                    "min_change": min_change,
                    "max_change": max_change,
                    "range": max_change - min_change,
                }
            )

        # 按影响范围排序
        param_impacts.sort(key=lambda x: abs(x["range"]), reverse=True)

        # 创建龙卷风图
        fig = go.Figure()

        parameters = [p["parameter"] for p in param_impacts]
        min_changes = [p["min_change"] for p in param_impacts]
        max_changes = [p["max_change"] for p in param_impacts]

        # 负向变化（左半边）
        fig.add_trace(
            go.Bar(
                name="最小变化",
                y=parameters,
                x=min_changes,
                orientation="h",
                marker_color="#d62728",
                text=[f"{v:+.1f}" for v in min_changes],
                textposition="auto",
            )
        )

        # 正向变化（右半边）
        fig.add_trace(
            go.Bar(
                name="最大变化",
                y=parameters,
                x=max_changes,
                orientation="h",
                marker_color="#2ca02c",
                text=[f"{v:+.1f}" for v in max_changes],
                textposition="auto",
            )
        )

        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            barmode="relative",
            height=max(300, 50 * len(parameters)),
            xaxis_title=f"{SENSITIVITY_METRICS[metric]['name']}变化",
            yaxis_title="参数",
            plot_bgcolor="white",
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
            ),
        )

        return fig

    def generate_line_chart(
        self,
        result: SensitivityResult,
        metric: str = "total_cost",
        title: Optional[str] = None,
    ) -> go.Figure:
        """
        生成折线图展示参数影响趋势。

        Args:
            result: 单参数分析结果
            metric: 要展示的指标
            title: 图表标题

        Returns:
            Plotly Figure 对象
        """
        param_config = ANALYZABLE_PARAMETERS.get(result.parameter_name, {})
        metric_config = SENSITIVITY_METRICS.get(metric, {})

        if title is None:
            title = f"{param_config.get('name', result.parameter_name)}对{metric_config.get('name', metric)}的影响"

        metric_values = [r.get("cost_data", {}).get(metric, 0) for r in result.results]

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=result.test_values,
                y=metric_values,
                mode="lines+markers",
                marker=dict(size=10),
                line=dict(width=2),
                text=[f"{v:.2f}" for v in metric_values],
                hovertemplate=(
                    f"{param_config.get('name', '参数值')}: %{{x:.2f}}<br>"
                    f"{metric_config.get('name', '指标值')}: %{{y:.2f}}<extra></extra>"
                ),
            )
        )

        # 标记基准点
        base_metric = None
        for i, v in enumerate(result.test_values):
            if abs(v - result.base_value) < 0.001:
                base_metric = metric_values[i]
                break

        if base_metric is not None:
            fig.add_vline(
                x=result.base_value,
                line_dash="dash",
                line_color="red",
                annotation_text=f"基准: {result.base_value}",
            )

        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            xaxis_title=f"{param_config.get('name', result.parameter_name)} ({param_config.get('unit', '')})",
            yaxis_title=f"{metric_config.get('name', metric)} ({metric_config.get('unit', '')})",
            height=400,
            plot_bgcolor="white",
        )

        return fig

    def generate_sensitivity_heatmap(
        self, results: Dict[str, SensitivityResult], title: str = "参数敏感度热力图"
    ) -> go.Figure:
        """
        生成敏感度热力图。

        Args:
            results: 多参数分析结果
            title: 图表标题

        Returns:
            Plotly Figure 对象
        """
        # 构建敏感度矩阵
        parameters = list(results.keys())
        metrics = list(SENSITIVITY_METRICS.keys())

        sensitivity_matrix = []
        param_names = []

        for param in parameters:
            result = results[param]
            row = [result.sensitivities.get(m, 0) for m in metrics]
            sensitivity_matrix.append(row)
            param_config = ANALYZABLE_PARAMETERS.get(param, {})
            param_names.append(param_config.get("name", param))

        metric_names = [SENSITIVITY_METRICS[m]["name"] for m in metrics]

        fig = go.Figure(
            data=go.Heatmap(
                z=sensitivity_matrix,
                x=metric_names,
                y=param_names,
                colorscale=[
                    [0, "#2ca02c"],  # 低敏感度 - 绿色
                    [0.5, "#ffbb33"],  # 中等 - 黄色
                    [1, "#d62728"],  # 高敏感度 - 红色
                ],
                colorbar=dict(title="敏感度系数"),
                text=[[f"{v:.3f}" for v in row] for row in sensitivity_matrix],
                texttemplate="%{text}",
                textfont={"size": 12},
            )
        )

        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            xaxis_title="指标",
            yaxis_title="参数",
            height=max(300, 60 * len(parameters)),
        )

        return fig

    def generate_sensitivity_report(
        self,
        result: SensitivityResult,
    ) -> str:
        """
        生成敏感度分析报告。

        Args:
            result: 分析结果

        Returns:
            格式化的报告文本
        """
        param_config = ANALYZABLE_PARAMETERS.get(result.parameter_name, {})
        lines = []
        lines.append("=" * 60)
        lines.append(f"参数敏感度分析报告: {param_config.get('name', result.parameter_name)}")
        lines.append("=" * 60)
        lines.append("")

        # 参数信息
        lines.append(f"基准值: {result.base_value} {param_config.get('unit', '')}")
        lines.append(f"测试范围: {min(result.test_values):.2f} - {max(result.test_values):.2f}")
        lines.append("")

        # 敏感度系数
        lines.append("【敏感度系数】")
        lines.append("-" * 40)
        lines.append(f"{'指标':<20} {'敏感度':>10}")
        lines.append("-" * 40)

        for metric, sensitivity in result.impact_ranking:
            config = SENSITIVITY_METRICS.get(metric, {})
            name = config.get("name", metric)
            lines.append(f"{name:<20} {sensitivity:>10.4f}")

        lines.append("-" * 40)
        lines.append("")

        # 解读
        lines.append("【分析解读】")
        if result.impact_ranking:
            most_sensitive = result.impact_ranking[0]
            metric_config = SENSITIVITY_METRICS.get(most_sensitive[0], {})
            lines.append(
                f"该参数对{metric_config.get('name', most_sensitive[0])}影响最大，"
                f"敏感度系数为 {most_sensitive[1]:.4f}"
            )

            if abs(most_sensitive[1]) > 1:
                lines.append("指标变化幅度大于参数变化幅度，需重点关注。")
            elif abs(most_sensitive[1]) > 0.5:
                lines.append("指标变化幅度与参数变化幅度相近。")
            else:
                lines.append("指标对参数变化不太敏感。")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
