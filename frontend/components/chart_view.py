"""
企业简约风格图表视图组件
"""

import plotly.graph_objects as go
import streamlit as st

# 企业配色
ENTERPRISE_COLORS = {
    "primary": "#2C3E50",
    "secondary": "#34495E",
    "accent": "#3498DB",
    "success": "#27AE60",
    "warning": "#F39C12",
    "danger": "#E74C3C",
    "light": "#ECF0F1",
    "gray": "#95A5A6",
}


def enterprise_chart_template():
    """
    返回企业风格的图表模板配置

    Returns:
        dict: 图表配置字典
    """
    return {
        "font": {"family": "Arial, sans-serif", "size": 12, "color": "#2C3E50"},
        "paper_bgcolor": "white",
        "plot_bgcolor": "white",
        "margin": {"l": 10, "r": 10, "t": 10, "b": 10},
        "xaxis": {
            "gridcolor": "#ECF0F1",
            "zerolinecolor": "#ECF0F1",
        },
        "yaxis": {
            "gridcolor": "#ECF0F1",
            "zerolinecolor": "#ECF0F1",
        },
    }


def create_cost_breakdown_chart(cost_result):
    """
    创建成本分解饼图

    Args:
        cost_result: 成本结果字典

    Returns:
        plotly.graph_objects.Figure: 饼图对象
    """
    labels = list(cost_result.get("cost_breakdown", {}).keys())
    values = list(cost_result.get("cost_breakdown", {}).values())

    if not labels or not values:
        return None

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.5,
                marker_colors=[
                    ENTERPRISE_COLORS["accent"],
                    ENTERPRISE_COLORS["success"],
                    ENTERPRISE_COLORS["primary"],
                    ENTERPRISE_COLORS["warning"],
                    ENTERPRISE_COLORS["danger"],
                ][: len(labels)],
                textinfo="percent+label",
                textposition="inside",
                textfont_size=11,
                hovertemplate="<b>%{label}</b><br>金额: ¥%{value:,.2}<br>占比: %{percent}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title={
            "text": "成本结构分析",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 16, "color": ENTERPRISE_COLORS["primary"]},
        },
        height=400,
        **enterprise_chart_template(),
    )

    return fig


def create_cost_comparison_chart(solutions_history):
    """
    创建多方案成本对比图

    Args:
        solutions_history: 求解方案历史列表

    Returns:
        plotly.graph_objects.Figure: 柱状图对象
    """
    if not solutions_history:
        return None

    names = [sol["name"] for sol in solutions_history]
    [sol["cost_result"]["total_cost"] for sol in solutions_history]
    transport_costs = [sol["cost_result"]["transport_cost"] for sol in solutions_history]
    carbon_costs = [sol["cost_result"].get("carbon_cost", 0) for sol in solutions_history]
    penalty_costs = [sol["cost_result"]["penalty_cost"] for sol in solutions_history]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="运输成本",
            x=names,
            y=transport_costs,
            marker_color=ENTERPRISE_COLORS["accent"],
            text=[f"¥{v:,.0f}" for v in transport_costs],
            textposition="auto",
            textfont_size=10,
        )
    )

    fig.add_trace(
        go.Bar(
            name="碳排成本",
            x=names,
            y=carbon_costs,
            marker_color=ENTERPRISE_COLORS["success"],
            text=[f"¥{v:,.2f}" for v in carbon_costs],
            textposition="auto",
            textfont_size=10,
        )
    )

    fig.add_trace(
        go.Bar(
            name="惩罚成本",
            x=names,
            y=penalty_costs,
            marker_color=ENTERPRISE_COLORS["danger"],
            text=[f"¥{v:,.0f}" for v in penalty_costs],
            textposition="auto",
            textfont_size=10,
        )
    )

    fig.update_layout(
        title={
            "text": "多方案成本对比",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 16, "color": ENTERPRISE_COLORS["primary"]},
        },
        barmode="stack",
        height=500,
        xaxis_title="求解方案",
        yaxis_title="成本 (元)",
        legend_title="成本类型",
        **enterprise_chart_template(),
    )

    return fig


def create_performance_comparison_chart(solutions_history):
    """
    创建性能对比图

    Args:
        solutions_history: 求解方案历史列表

    Returns:
        plotly.graph_objects.Figure: 柱状图对象
    """
    if not solutions_history:
        return None

    names = [sol["name"] for sol in solutions_history]
    solve_times = [sol["solve_time"] for sol in solutions_history]
    distances = [sol["solution"]["total_distance"] for sol in solutions_history]
    [sol["cost_result"]["carbon_emission_kg"] for sol in solutions_history]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="求解时间 (秒)",
            x=names,
            y=solve_times,
            marker_color=ENTERPRISE_COLORS["accent"],
            yaxis="y",
            text=[f"{v:.2f}s" for v in solve_times],
            textposition="auto",
            textfont_size=10,
        )
    )

    fig.add_trace(
        go.Bar(
            name="总距离 (km)",
            x=names,
            y=distances,
            marker_color=ENTERPRISE_COLORS["success"],
            yaxis="y2",
            text=[f"{v:.1f}km" for v in distances],
            textposition="auto",
            textfont_size=10,
        )
    )

    fig.update_layout(
        title={
            "text": "性能指标对比",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 16, "color": ENTERPRISE_COLORS["primary"]},
        },
        barmode="group",
        height=500,
        xaxis_title="求解方案",
        yaxis={
            "title": "求解时间 (秒)",
            "titlefont": {"color": ENTERPRISE_COLORS["accent"]},
            "tickfont": {"color": ENTERPRISE_COLORS["accent"]},
        },
        yaxis2={
            "title": "总距离 (km)",
            "titlefont": {"color": ENTERPRISE_COLORS["success"]},
            "tickfont": {"color": ENTERPRISE_COLORS["success"]},
            "overlaying": "y",
            "side": "right",
        },
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        **enterprise_chart_template(),
    )

    return fig


def create_carbon_emission_chart(solutions_history):
    """
    创建碳排放对比图

    Args:
        solutions_history: 求解方案历史列表

    Returns:
        plotly.graph_objects.Figure: 柱状图对象
    """
    if not solutions_history:
        return None

    names = [sol["name"] for sol in solutions_history]
    carbon_emissions = [sol["cost_result"]["carbon_emission_kg"] for sol in solutions_history]

    # 找出最低碳排放的方案
    min_carbon = min(carbon_emissions)
    colors = [
        ENTERPRISE_COLORS["success"] if c == min_carbon else ENTERPRISE_COLORS["accent"]
        for c in carbon_emissions
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=names,
                y=carbon_emissions,
                marker_color=colors,
                text=[f"{c:.2f} kg" for c in carbon_emissions],
                textposition="auto",
                textfont_size=12,
                hovertemplate="<b>%{x}</b><br>碳排放: %{y:.2f} kg CO₂<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title={
            "text": "各方案碳排放量对比",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 16, "color": ENTERPRISE_COLORS["primary"]},
        },
        xaxis_title="求解方案",
        yaxis_title="碳排放量 (kg CO₂)",
        height=450,
        **enterprise_chart_template(),
    )

    return fig


def create_vehicle_utilization_chart(solution, vehicle_config):
    """
    创建车辆利用率图表

    Args:
        solution: 求解结果
        vehicle_config: 车辆配置

    Returns:
        plotly.graph_objects.Figure: 堆叠柱状图对象
    """
    if not solution or not vehicle_config:
        return None

    vehicles_used = solution.get("vehicles_used", {})

    fig = go.Figure()

    for v_type, config in vehicle_config.items():
        used = vehicles_used.get(v_type, 0)
        available = config.get("count", 0)
        unused = max(0, available - used)

        fig.add_trace(
            go.Bar(
                name=v_type,
                x=["已使用", "未使用"],
                y=[used, unused],
                marker_color=ENTERPRISE_COLORS["accent"]
                if v_type == "4.2m"
                else (
                    ENTERPRISE_COLORS["success"]
                    if v_type == "7.6m"
                    else ENTERPRISE_COLORS["primary"]
                ),
                text=[used, unused],
                textposition="auto",
                textfont_size=11,
            )
        )

    fig.update_layout(
        title={
            "text": "车辆利用率分析",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 16, "color": ENTERPRISE_COLORS["primary"]},
        },
        barmode="stack",
        height=400,
        xaxis_title="使用状态",
        yaxis_title="车辆数量",
        legend_title="车型",
        **enterprise_chart_template(),
    )

    return fig


def create_time_analysis_chart(cost_result):
    """
    创建时间分解分析图

    Args:
        cost_result: 成本结果字典

    Returns:
        plotly.graph_objects.Figure: 饼图对象
    """
    time_components = {
        "行驶时间": cost_result.get("driving_time_min", 0),
        "服务时间": cost_result.get("service_time_min", 0),
        "等待时间": cost_result.get("waiting_time_min", 0),
    }

    # 过滤掉值为0的组件
    time_components = {k: v for k, v in time_components.items() if v > 0}

    if not time_components:
        return None

    labels = list(time_components.keys())
    values = list(time_components.values())

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                marker_colors=[
                    ENTERPRISE_COLORS["accent"],
                    ENTERPRISE_COLORS["success"],
                    ENTERPRISE_COLORS["warning"],
                ][: len(labels)],
                textinfo="percent+label",
                textposition="inside",
                textfont_size=11,
                hovertemplate="<b>%{label}</b><br>时间: %{value:.1f} 分钟<br>占比: %{percent}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title={
            "text": "时间构成分析",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 16, "color": ENTERPRISE_COLORS["primary"]},
        },
        height=400,
        **enterprise_chart_template(),
    )

    return fig


def create_efficiency_indicators(cost_result, solution):
    """
    创建效率指标图

    Args:
        cost_result: 成本结果字典
        solution: 求解结果

    Returns:
        plotly.graph_objects.Figure: 指标图对象
    """
    try:
        from core.cost import calculate_cost_efficiency_metrics

        efficiency = calculate_cost_efficiency_metrics(cost_result, solution)
    except Exception:  # noqa: B001
        efficiency = {
            "cost_per_km": 0,
            "cost_per_customer": 0,
            "carbon_per_km": 0,
            "labor_efficiency": 0,
        }

    fig = go.Figure()

    indicators = [
        {"name": "单位距离成本", "value": efficiency["cost_per_km"], "suffix": "元/km"},
        {"name": "单位客户成本", "value": efficiency["cost_per_customer"], "suffix": "元/客户"},
        {"name": "单位距离碳排放", "value": efficiency["carbon_per_km"], "suffix": "kg/km"},
        {"name": "人工效率", "value": efficiency["labor_efficiency"] * 100, "suffix": "%"},
    ]

    for i, indicator in enumerate(indicators):
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=indicator["value"],
                name=indicator["name"],
                number={
                    "font": {"size": 24, "color": ENTERPRISE_COLORS["primary"]},
                    "format": f".{2 if '%' not in indicator['suffix'] else 1}f",
                    "suffix": f" {indicator['suffix']}",
                },
                title={
                    "text": indicator["name"],
                    "font": {"size": 14, "color": ENTERPRISE_COLORS["gray"]},
                },
                domain={"x": [(i * 0.25), ((i + 1) * 0.25 - 0.05)], "y": [0, 1]},
            )
        )

    fig.update_layout(
        title={
            "text": "运营效率指标",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 16, "color": ENTERPRISE_COLORS["primary"]},
        },
        height=300,
        **enterprise_chart_template(),
    )

    return fig


def enterprise_metric_row(metrics):
    """
    创建企业风格的指标行

    Args:
        metrics: 指标字典列表，每个包含 'title', 'value', 'delta' (可选), 'delta_type' (可选)
    """
    num_columns = len(metrics)
    columns = st.columns(num_columns)

    for _i, (col, metric) in enumerate(zip(columns, metrics, strict=False)):
        with col:
            delta_type = metric.get("delta_type", "neutral")
            delta_class = ""

            if delta_type == "positive":
                delta_class = "positive"
            elif delta_type == "negative":
                delta_class = "negative"

            delta_html = ""
            if metric.get("delta"):
                delta_html = f'<div class="metric-delta {delta_class}">{metric["delta"]}</div>'

            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-title">{metric["title"]}</div>
                <div class="metric-value">{metric["value"]}</div>
                {delta_html}
            </div>
            """,
                unsafe_allow_html=True,
            )
