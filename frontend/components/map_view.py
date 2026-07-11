"""
企业简约风格地图视图组件
"""

import folium
import pandas as pd
import streamlit as st

# 企业配色
ENTERPRISE_COLORS = {
    "primary": "#2C3E504D",  # 透明主色
    "accent": "#3498DB",  # 强调色
    "success": "#27AE60",  # 成功绿
    "warning": "#F39C12",  # 警告橙
    "danger": "#E74C3C",  # 危险红
}


def create_enterprise_map(customers_df=None, solution=None, vehicle_config=None):
    """
    创建企业简约风格的地图

    Args:
        customers_df: 客户数据 DataFrame
        solution: 求解结果
        vehicle_config: 车辆配置

    Returns:
        folium.Map: 地图对象
    """
    if customers_df is not None:
        # 计算中心点
        center_lat = customers_df["lat"].mean()
        center_lon = customers_df["lon"].mean()
    else:
        # 默认中心点（北京）
        center_lat = 39.9042
        center_lon = 116.4074

    # 创建地图
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="OpenStreetMap")

    # 添加企业风格的控制面板
    m.add_child(folium.plugins.MeasureControl())

    # 如果有求解结果，绘制路线
    if solution and solution.get("routes"):
        route_colors = {
            "4.2m": ENTERPRISE_COLORS["accent"],
            "7.6m": ENTERPRISE_COLORS["success"],
            "9.6m": ENTERPRISE_COLORS["primary"].replace("4D", "CC"),  # 更深的颜色
        }

        for route in solution["routes"]:
            vehicle_type = route["vehicle_type"]
            color = route.get(
                "vehicle_color", route_colors.get(vehicle_type, ENTERPRISE_COLORS["accent"])
            )
            stops = route["stops"]

            # 绘制路线
            coords = [(s["lat"], s["lon"]) for s in stops]
            if len(coords) > 1:
                folium.PolyLine(
                    coords,
                    color=color,
                    weight=3,
                    opacity=0.7,
                    popup=f"""
                    <div style="font-family: Arial, sans-serif;">
                        <strong>{vehicle_type}</strong><br>
                        距离: {route["distance_km"]:.1f} km<br>
                        载重: {route.get("total_demand", 0)} 件
                    </div>
                    """,
                ).add_to(m)

            # 绘制站点
            for _i, stop in enumerate(stops):
                node = stop.get("node", 0)
                lat = stop["lat"]
                lon = stop["lon"]

                # 仓库标记
                if node == 0:
                    folium.Marker(
                        [lat, lon],
                        popup="""
                        <div style="font-family: Arial, sans-serif;">
                            <strong>🏠 配送中心</strong>
                        </div>
                        """,
                        icon=folium.Icon(color="darkred", icon="warehouse", prefix="fa"),
                    ).add_to(m)
                else:
                    # 客户标记
                    is_late = stop.get("is_late", False)
                    marker_color = (
                        ENTERPRISE_COLORS["warning"] if is_late else ENTERPRISE_COLORS["accent"]
                    )

                    popup_html = f"""
                    <div style="font-family: Arial, sans-serif;">
                        <strong>{stop.get("customer_name", f"客户{node}")}</strong><br>
                        <hr style="border: 1px solid #ddd; margin: 8px 0;">
                        📦 需求量: {stop.get("demand", 0)} 件<br>
                        ⏰ 到达时间: {stop.get("arrival_time", 0)} 分钟<br>
                        📅 时间窗: {stop.get("tw_earliest", 0)} - {stop.get("tw_latest", 0)}
                    """

                    if is_late:
                        popup_html += f"<br><strong style='color: {ENTERPRISE_COLORS['danger']}'>⚠️ 迟到: {stop.get('late_minutes', 0)} 分钟</strong>"

                    popup_html += "</div>"

                    folium.CircleMarker(
                        [lat, lon],
                        radius=10,
                        popup=folium.Popup(popup_html, max_width=300),
                        color=marker_color,
                        fill=True,
                        fillColor=marker_color,
                        fillOpacity=0.3,
                        weight=2,
                    ).add_to(m)

        # 添加企业风格图例
        legend_html = f"""
        <div style="
            position: fixed;
            bottom: 30px;
            left: 30px;
            z-index: 1000;
            background-color: white;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-family: Arial, sans-serif;
            font-size: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <strong style="color: #333; margin-bottom: 8px; display: block;">车型图例</strong>
            <div style="margin-bottom: 4px;">
                <span style="background: {route_colors["4.2m"]}; width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>
                4.2m 小型车
            </div>
            <div style="margin-bottom: 4px;">
                <span style="background: {route_colors["7.6m"]}; width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>
                7.6m 中型车
            </div>
            <div>
                <span style="background: {route_colors["9.6m"]}; width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>
                9.6m 大型车
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

    elif customers_df is not None:
        # 只显示客户位置
        for _, row in customers_df.iterrows():
            if row["id"] == 0:
                folium.Marker(
                    [row["lat"], row["lon"]],
                    popup=row["name"],
                    icon=folium.Icon(color="darkred", icon="warehouse", prefix="fa"),
                ).add_to(m)
            else:
                folium.CircleMarker(
                    [row["lat"], row["lon"]],
                    radius=8,
                    popup=row["name"],
                    color=ENTERPRISE_COLORS["accent"],
                    fill=True,
                    fillColor=ENTERPRISE_COLORS["accent"],
                    fillOpacity=0.3,
                    weight=2,
                ).add_to(m)

    return m


def display_route_statistics(solution):
    """
    显示路线统计信息

    Args:
        solution: 求解结果
    """
    if not solution or not solution.get("routes"):
        return

    enterprise_section_header("路线统计")

    # 路线汇总
    routes_data = []
    total_distance = 0
    total_customers = 0
    total_late = 0

    for route in solution["routes"]:
        customer_count = len([s for s in route["stops"] if s.get("node", 0) > 0])
        distance = route.get("distance_km", 0)
        late_minutes = route.get("late_minutes", 0)

        routes_data.append(
            {
                "车型": route["vehicle_type"],
                "车辆ID": route.get("vehicle_id", 0) + 1,
                "客户数": customer_count,
                "距离 (km)": f"{distance:.2f}",
                "载重": route.get("total_demand", 0),
                "迟到 (分钟)": late_minutes if late_minutes > 0 else "准时",
            }
        )

        total_distance += distance
        total_customers += customer_count
        total_late += late_minutes

    routes_df = pd.DataFrame(routes_data)
    st.dataframe(routes_df, use_container_width=True, hide_index=True)

    # 汇总统计
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("总距离", f"{total_distance:.2f} km")
    with col2:
        st.metric("服务客户数", f"{total_customers} 家")
    with col3:
        st.metric("总迟到时间", f"{total_late} 分钟")


def display_route_details(solution):
    """
    显示详细的路线信息

    Args:
        solution: 求解结果
    """
    if not solution or not solution.get("routes"):
        return

    enterprise_section_header("详细路线信息")

    for route in solution["routes"]:
        with st.expander(
            f"🚛 {route['vehicle_type']} - 车辆 {route.get('vehicle_id', 0) + 1}", expanded=False
        ):
            # 路线概览
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("距离", f"{route.get('distance_km', 0):.2f} km")
            with col2:
                st.metric("载重", f"{route.get('total_demand', 0)} 件")
            with col3:
                st.metric("迟到", f"{route.get('late_minutes', 0)} 分钟")

            # 站点详情
            stops_data = []
            for stop in route["stops"]:
                if stop.get("node", 0) == 0:  # 跳过仓库
                    continue

                stop.get("arrival_time", 0)
                stop.get("tw_earliest", 0)
                stop.get("tw_latest", 0)
                stop.get("is_late", False)

                # stops_data.append({
                #     '节点': stop.get('node', 0),
                #     '客户': stop.get('customer_name', ''),
                #     '需求': stop.get('demand', 0),
                #     '到达时间': f"{arrival_time}分钟",
                #     '时间窗': f"{tw_earliest}-{tw_latest}",
                #     '迟到': f"{stop.get('late_minutes', 0)}分钟" if is_late else '准时'
                # })

            if stops_data:
                stops_df = pd.DataFrame(stops_data)
                st.dataframe(stops_df, use_container_width=True, hide_index=True)


def enterprise_section_header(title: str):
    """企业风格章节标题"""
    st.markdown(
        f"""
    <div style="
        color: #2C3E50;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #3498DB;
    ">{title}</div>
    """,
        unsafe_allow_html=True,
    )
