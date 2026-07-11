"""
视图组件模块

提供地图、成本图表和甘特图组件，供 Streamlit 应用使用。
"""

from typing import Any

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def create_route_map(
    solution: dict[str, Any],
    customers_df: pd.DataFrame,
) -> folium.Map:
    """
    创建配送路线地图。

    Args:
        solution: 求解结果，包含 routes
        customers_df: 客户数据 DataFrame

    Returns:
        folium.Map 地图对象
    """
    center_lat = customers_df["lat"].mean()
    center_lon = customers_df["lon"].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles="OpenStreetMap",
    )

    # 添加 MeasureControl
    m.add_child(folium.plugins.MeasureControl())

    if not solution or not solution.get("routes"):
        # 只显示客户位置
        for _, row in customers_df.iterrows():
            node_id = int(row.get("id", 0))
            if node_id == 0:
                folium.Marker(
                    [row["lat"], row["lon"]],
                    popup=str(row.get("name", "仓库")),
                    icon=folium.Icon(color="darkred", icon="warehouse", prefix="fa"),
                ).add_to(m)
            else:
                folium.CircleMarker(
                    [row["lat"], row["lon"]],
                    radius=8,
                    popup=str(row.get("name", f"客户{node_id}")),
                    color="#3498DB",
                    fill=True,
                    fillColor="#3498DB",
                    fillOpacity=0.3,
                    weight=2,
                ).add_to(m)
        return m

    route_colors = {
        "4.2m": "#1f77b4",
        "7.6m": "#2ca02c",
        "9.6m": "#9467bd",
    }

    for route in solution["routes"]:
        vehicle_type = route.get("vehicle_type", "4.2m")
        color = route.get("vehicle_color", route_colors.get(vehicle_type, "#1f77b4"))
        stops = route.get("stops", [])

        # 绘制路线
        coords = [(s["lat"], s["lon"]) for s in stops]
        if len(coords) > 1:
            folium.PolyLine(
                coords,
                color=color,
                weight=4,
                opacity=0.8,
                popup=folium.Popup(
                    f"<b>{vehicle_type}</b><br>"
                    f"距离: {route.get('distance_km', 0):.1f} km<br>"
                    f"载重: {route.get('total_demand', 0)} 件",
                    max_width=200,
                ),
            ).add_to(m)

        # 绘制站点
        for stop in stops:
            node = stop.get("node", 0)
            lat = stop["lat"]
            lon = stop["lon"]

            if node == 0:
                # 仓库
                folium.Marker(
                    [lat, lon],
                    popup="<b>配送中心</b>",
                    icon=folium.Icon(color="darkred", icon="warehouse", prefix="fa"),
                ).add_to(m)
            else:
                # 客户
                is_late = stop.get("is_late", False)
                marker_color = "#E74C3C" if is_late else "#3498DB"

                popup_html = (
                    f"<b>{stop.get('customer_name', f'客户{node}')}</b><br>"
                    f"需求: {stop.get('demand', 0)} 件<br>"
                    f"到达: {stop.get('arrival_time', 0)} 分钟<br>"
                )
                if is_late:
                    popup_html += (
                        f"<span style='color:red;'>迟到: {stop.get('late_minutes', 0)} 分钟</span>"
                    )

                folium.CircleMarker(
                    [lat, lon],
                    radius=10,
                    popup=folium.Popup(popup_html, max_width=250),
                    color=marker_color,
                    fill=True,
                    fillColor=marker_color,
                    fillOpacity=0.3,
                    weight=2,
                ).add_to(m)

    return m


def create_cost_stack_chart(
    cost_result: dict[str, Any],
) -> go.Figure:
    """
    创建成本堆积柱状图。

    Args:
        cost_result: 成本结果字典

    Returns:
        plotly.graph_objects.Figure 图表对象
    """
    breakdown = cost_result.get("cost_breakdown", {})
    labels = list(breakdown.keys())
    values = list(breakdown.values())

    colors = ["#1f77b4", "#2ca02c", "#9467bd", "#d62728", "#ff7f0e"]

    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=colors[: len(labels)],
                text=[f"¥{v:,.2f}" for v in values],
                textposition="auto",
            )
        ]
    )

    fig.update_layout(
        title="成本结构分析",
        xaxis_title="成本类型",
        yaxis_title="金额 (元)",
        height=400,
        plot_bgcolor="white",
        margin={"l": 40, "r": 40, "t": 60, "b": 40},
    )

    return fig


def create_gantt_chart(
    solution: dict[str, Any],
    vehicle_config: dict[str, Any] | None = None,
) -> go.Figure:
    """
    创建车辆作业甘特图。

    Args:
        solution: 求解结果，包含 routes
        vehicle_config: 车型配置

    Returns:
        plotly.graph_objects.Figure 图表对象
    """
    df_tasks = []

    for route in solution.get("routes", []):
        vehicle_id = route.get("vehicle_id", 0)
        vehicle_type = route.get("vehicle_type", "unknown")
        stops = route.get("stops", [])

        task_name = f"车辆 {vehicle_id + 1} ({vehicle_type})"

        for i in range(len(stops) - 1):
            stop = stops[i]
            next_stop = stops[i + 1]
            node = stop.get("node", 0)

            arrival = stop.get("arrival_time", 0)
            departure = stop.get("arrival_time", 0) + stop.get("service_time", 0)
            next_arrival = next_stop.get("arrival_time", 0)

            # 行驶段
            if node == 0:
                task_label = f"仓库→{next_stop.get('customer_name', '')}"
                task_color = "#3498DB"
            else:
                task_label = f"客户{node}→"
                task_color = "#3498DB"

            df_tasks.append(
                {
                    "Task": task_name,
                    "Start": arrival,
                    "Finish": next_arrival,
                    "Resource": "行驶",
                    "Detail": task_label,
                    "Color": task_color,
                }
            )

            # 服务段（客户节点）
            if node > 0 and departure > arrival:
                df_tasks.append(
                    {
                        "Task": task_name,
                        "Start": arrival,
                        "Finish": departure,
                        "Resource": "服务",
                        "Detail": f"服务客户{node}",
                        "Color": "#27AE60",
                    }
                )

    if not df_tasks:
        fig = go.Figure()
        fig.update_layout(
            title="车辆作业时间线 (暂无数据)",
            height=300,
        )
        return fig

    df = pd.DataFrame(df_tasks)

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Resource",
        color_discrete_map={"行驶": "#3498DB", "服务": "#27AE60"},
        hover_data=["Detail"],
    )

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        title="车辆作业甘特图",
        xaxis_title="时间 (分钟，从0:00起)",
        yaxis_title="车辆",
        height=400 + len(solution.get("routes", [])) * 30,
    )

    return fig
