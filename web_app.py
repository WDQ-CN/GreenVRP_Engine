"""
GreenVRP Engine Web 启动器

基于 Streamlit 的可视化 Web 界面，提供：
- 交互式求解配置
- 实时可视化地图
- 成本分析报告
- 路线对比功能

启动方式：
    streamlit run web_app.py
"""

import os
import sys
import time
from datetime import datetime

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from folium import plugins
from streamlit_folium import st_folium

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.vehicles import DEFAULT_VEHICLE_CONFIG
from core.cost import calculate_green_cost
from core.solver import GreenVRPSolver, solve_with_multiple_strategies

# 页面配置
st.set_page_config(
    page_title="绿色物流路径优化引擎",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义样式
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2ca02c;
        margin-top: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .cost-item {
        display: flex;
        justify-content: space-between;
        padding: 0.5rem 0;
        border-bottom: 1px solid #e0e0e0;
    }
</style>
""",
    unsafe_allow_html=True,
)


def init_session_state():
    """初始化会话状态。"""
    if "solution" not in st.session_state:
        st.session_state.solution = None
    if "cost_result" not in st.session_state:
        st.session_state.cost_result = None
    if "customers_df" not in st.session_state:
        st.session_state.customers_df = None
    if "solve_time" not in st.session_state:
        st.session_state.solve_time = 0
    if "solutions_history" not in st.session_state:
        st.session_state.solutions_history = []  # 存储多个方案
    if "current_solution_name" not in st.session_state:
        st.session_state.current_solution_name = None


def load_default_data():
    """加载默认客户数据。"""
    try:
        df = pd.read_csv("data/mock_customers.csv")
        return df
    except FileNotFoundError:
        # 返回示例数据
        data = {
            "id": [0, 1, 2, 3, 4, 5],
            "name": ["仓库", "客户A", "客户B", "客户C", "客户D", "客户E"],
            "lat": [39.9042, 39.9123, 39.9456, 39.9876, 40.0234, 39.9678],
            "lon": [116.4074, 116.3456, 116.3789, 116.4123, 116.4567, 116.5234],
            "demand": [0, 45, 67, 89, 34, 56],
            "service_time_min": [0, 15, 20, 25, 12, 18],
            "tw_earliest": [480, 500, 520, 480, 550, 600],
            "tw_latest": [960, 600, 640, 580, 680, 720],
        }
        return pd.DataFrame(data)


def create_map(customers_df, solution=None):
    """创建可视化地图。"""
    # 计算中心点
    center_lat = customers_df["lat"].mean()
    center_lon = customers_df["lon"].mean()

    # 创建地图
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="OpenStreetMap")

    # 如果有求解结果，绘制路线
    if solution and solution.get("routes"):
        route_colors = {
            "4.2m": "#1f77b4",
            "7.6m": "#2ca02c",
            "9.6m": "#9467bd",
        }

        for route in solution["routes"]:
            vehicle_type = route["vehicle_type"]
            color = route.get("vehicle_color", route_colors.get(vehicle_type, "#1f77b4"))
            stops = route["stops"]

            # 绘制路线
            coords = [(s["lat"], s["lon"]) for s in stops]
            if len(coords) > 1:
                folium.PolyLine(
                    coords,
                    color=color,
                    weight=4,
                    opacity=0.8,
                    popup=f"{vehicle_type} - 距离: {route['distance_km']:.1f}km",
                ).add_to(m)

            # 绘制站点
            for i, stop in enumerate(stops):
                node = stop.get("node", 0)
                lat = stop["lat"]
                lon = stop["lon"]

                # 仓库标记
                if node == 0:
                    folium.Marker(
                        [lat, lon],
                        popup=f"仓库",
                        icon=folium.Icon(color="red", icon="home", prefix="fa"),
                    ).add_to(m)
                else:
                    # 客户标记
                    is_late = stop.get("is_late", False)
                    marker_color = "orange" if is_late else "blue"

                    popup_html = f"""
                    <b>{stop.get('customer_name', f'客户{node}')}</b><br>
                    需求: {stop.get('demand', 0)} 件<br>
                    到达: {stop.get('arrival_time', 0)} 分钟<br>
                    时间窗: {stop.get('tw_earliest', 0)} - {stop.get('tw_latest', 0)}
                    """
                    if is_late:
                        popup_html += f"<br><span style='color:red'>迟到: {stop.get('late_minutes', 0)} 分钟</span>"

                    folium.CircleMarker(
                        [lat, lon],
                        radius=10,
                        popup=folium.Popup(popup_html, max_width=300),
                        color=marker_color,
                        fill=True,
                        fillColor=marker_color,
                        fillOpacity=0.6,
                    ).add_to(m)

        # 添加图例
        legend_html = """
        <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000;
                    background-color: white; padding: 10px; border: 2px solid grey;
                    border-radius: 5px;">
            <b>车型图例</b><br>
            <i style="background:#1f77b4; width:20px; height:4px; display:inline-block;"></i> 4.2m 小型车<br>
            <i style="background:#2ca02c; width:20px; height:4px; display:inline-block;"></i> 7.6m 中型车<br>
            <i style="background:#9467bd; width:20px; height:4px; display:inline-block;"></i> 9.6m 大型车
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
    else:
        # 只显示客户位置 (使用 NumPy 向量化优化)
        customer_data = customers_df[["id", "lat", "lon", "name"]].values
        for row in customer_data:
            cust_id, lat, lon, name = int(row[0]), row[1], row[2], row[3]
            if cust_id == 0:
                folium.Marker(
                    [lat, lon],
                    popup=name,
                    icon=folium.Icon(color="red", icon="home", prefix="fa"),
                ).add_to(m)
            else:
                folium.CircleMarker(
                    [lat, lon],
                    radius=8,
                    popup=name,
                    color="blue",
                    fill=True,
                    fillColor="blue",
                    fillOpacity=0.6,
                ).add_to(m)

    return m


def display_cost_analysis(cost_result, solution):
    """显示成本分析。"""
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("成本构成")
        # 成本饼图
        labels = list(cost_result["cost_breakdown"].keys())
        values = list(cost_result["cost_breakdown"].values())

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.4,
                    marker_colors=["#1f77b4", "#2ca02c", "#9467bd", "#d62728", "#ff7f0e"],
                )
            ]
        )
        fig.update_layout(height=400, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("关键指标")
        # 指标卡片
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("总成本", f"¥{cost_result['total_cost']:,.2f}")
        with m2:
            st.metric("碳排放量", f"{cost_result['carbon_emission_kg']:,.1f} kg")
        with m3:
            st.metric("总距离", f"{cost_result['total_distance_km']:,.1f} km")

        m4, m5, m6 = st.columns(3)
        with m4:
            st.metric("运输成本", f"¥{cost_result['transport_cost']:,.2f}")
        with m5:
            st.metric("人工成本", f"¥{cost_result['labor_cost']:,.2f}")
        with m6:
            st.metric("惩罚成本", f"¥{cost_result['penalty_cost']:,.2f}")

    # 详细成本表
    st.subheader("成本明细")
    # 修复除零错误
    total_cost = cost_result["total_cost"]
    cost_df = pd.DataFrame(
        {
            "项目": list(cost_result["cost_breakdown"].keys()),
            "金额 (元)": list(cost_result["cost_breakdown"].values()),
            "占比 (%)": [
                v / total_cost * 100 if total_cost > 0 else 0
                for v in cost_result["cost_breakdown"].values()
            ],
        }
    )
    st.dataframe(
        cost_df.style.format({"金额 (元)": "¥{:.2f}", "占比 (%)": "{:.1f}%"}),
        use_container_width=True,
    )


def display_routes_table(solution):
    """显示路线表格。"""
    st.subheader("路线详情")

    routes_data = []
    for route in solution["routes"]:
        customer_count = len([s for s in route["stops"] if s.get("node", 0) > 0])
        routes_data.append(
            {
                "车型": route["vehicle_type"],
                "客户数": customer_count,
                "距离 (km)": round(route["distance_km"], 2),
                "载重": route["total_demand"],
                "迟到 (分钟)": route.get("late_minutes", 0),
            }
        )

    df = pd.DataFrame(routes_data)
    st.dataframe(df, use_container_width=True)

    # 站点详情
    with st.expander("查看详细站点信息"):
        for route in solution["routes"]:
            st.markdown(f"**{route['vehicle_type']} - 车辆 {route['vehicle_id']}**")
            stops_data = []
            for stop in route["stops"]:
                stops_data.append(
                    {
                        "节点": stop.get("node"),
                        "客户": stop.get("customer_name", ""),
                        "需求": stop.get("demand", 0),
                        "到达时间": stop.get("arrival_time", 0),
                        "时间窗": f"{stop.get('tw_earliest', 0)}-{stop.get('tw_latest', 0)}",
                        "迟到": stop.get("late_minutes", 0),
                    }
                )
            st.dataframe(pd.DataFrame(stops_data), use_container_width=True)


def display_vehicle_usage(solution, vehicle_config):
    """显示车辆使用情况。"""
    st.subheader("车辆使用情况")

    vehicles_used = solution.get("vehicles_used", {})

    col1, col2 = st.columns(2)

    with col1:
        # 车辆使用柱状图
        fig = go.Figure()
        for v_type in vehicle_config.keys():
            used = vehicles_used.get(v_type, 0)
            available = vehicle_config[v_type].get("count", 0)
            fig.add_trace(
                go.Bar(
                    name=v_type,
                    x=["已使用", "未使用"],
                    y=[used, max(0, available - used)],
                    marker_color=vehicle_config[v_type].get("color", "#1f77b4"),
                )
            )
        fig.update_layout(barmode="stack", height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 车辆利用率
        utilization_data = []
        for v_type, config in vehicle_config.items():
            used = vehicles_used.get(v_type, 0)
            available = config.get("count", 0)
            utilization = used / available * 100 if available > 0 else 0
            utilization_data.append(
                {
                    "车型": v_type,
                    "可用数": available,
                    "使用数": used,
                    "利用率": f"{utilization:.1f}%",
                }
            )
        st.dataframe(pd.DataFrame(utilization_data), use_container_width=True)


def get_available_strategies():
    """返回可用的求解策略。"""
    return {
        "多策略最优": {
            "desc": "尝试多种策略组合，选择最优解",
            "func": solve_with_multiple_strategies,
        },
        "引导局部搜索": {
            "desc": "使用引导局部搜索算法",
            "strategy": 0,  # PATH_CHEAPEST_ARC
            "meta": 0,  # GUIDED_LOCAL_SEARCH
        },
        "禁忌搜索": {
            "desc": "使用禁忌搜索算法",
            "strategy": 0,  # PATH_CHEAPEST_ARC
            "meta": 1,  # TABU_SEARCH
        },
        "模拟退火": {
            "desc": "使用模拟退火算法",
            "strategy": 1,  # AUTOMATIC
            "meta": 2,  # SIMULATED_ANNEALING
        },
        "节约算法": {
            "desc": "使用节约算法构造初始解",
            "strategy": 2,  # SAVINGS
            "meta": 0,  # GUIDED_LOCAL_SEARCH
        },
        "扫帚算法": {
            "desc": "使用扫帚算法构造初始解",
            "strategy": 3,  # SWEEP
            "meta": 0,  # GUIDED_LOCAL_SEARCH
        },
    }


def solve_with_strategy(
    customers_df,
    vehicle_config,
    time_penalty_per_min,
    time_limit,
    strategy_info,
):
    """使用指定策略求解。"""
    from ortools.constraint_solver import routing_enums_pb2

    try:
        if "func" in strategy_info:
            # 使用预定义函数
            return strategy_info["func"](
                customers_df=customers_df,
                vehicle_config=vehicle_config,
                time_penalty_per_min=time_penalty_per_min,
                time_limit=time_limit,
            )
        else:
            # 使用自定义策略参数
            solver = GreenVRPSolver(
                customers_df=customers_df,
                vehicle_config=vehicle_config,
                time_penalty_per_min=time_penalty_per_min,
                search_time_limit=time_limit,
            )

            strategies = [
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
                routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC,
                routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
                routing_enums_pb2.FirstSolutionStrategy.SWEEP,
            ]
            metaheuristics = [
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
                routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH,
                routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
            ]

            return solver.solve_with_params(
                first_solution_strategy=strategies[strategy_info["strategy"]],
                metaheuristic=metaheuristics[strategy_info["meta"]],
                time_limit=time_limit,
            )
    except Exception as e:
        return {
            "routes": [],
            "total_distance": 0,
            "vehicles_used": {v_type: 0 for v_type in vehicle_config},
            "total_late_minutes": 0,
            "solution_status": f"ERROR: {str(e)}",
            "solve_time_seconds": 0,
        }


def display_comparison_tab():
    """显示方案对比标签页。"""
    st.subheader("多方案对比")

    # 获取可用策略
    strategies = get_available_strategies()

    # 策略选择
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 选择要对比的策略")
        selected_strategies = st.multiselect(
            "选择策略（可多选）",
            options=list(strategies.keys()),
            default=["多策略最优", "引导局部搜索", "禁忌搜索"],
            format_func=lambda x: f"{x} - {strategies[x]['desc']}",
        )

    with col2:
        st.markdown("### 求解设置")
        comparison_time_limit = st.slider(
            "每个策略求解时间（秒）", 10, 120, 30, key="comparison_time_limit"
        )
        use_parallel = st.checkbox("并行求解", value=True)

    # 求解按钮
    if st.button("🔄 开始多方案对比", type="primary", use_container_width=True):
        if not selected_strategies:
            st.warning("请至少选择一个策略!")
        elif st.session_state.customers_df is None:
            st.warning("请先加载客户数据!")
        else:
            # 清空历史
            st.session_state.solutions_history = []

            progress_bar = st.progress(0)
            status_text = st.empty()

            total = len(selected_strategies)

            for i, strategy_name in enumerate(selected_strategies):
                strategy_info = strategies[strategy_name]

                status_text.text(f"正在求解: {strategy_name} ({i+1}/{total})...")
                progress_bar.progress((i) / total)

                start_time = time.time()
                solution = solve_with_strategy(
                    st.session_state.customers_df,
                    st.session_state.get("vehicle_config", DEFAULT_VEHICLE_CONFIG),
                    10.0,  # time_penalty_per_min
                    comparison_time_limit,
                    strategy_info,
                )
                solve_time = time.time() - start_time

                # 计算成本
                try:
                    cost_result = {
                        "total_cost": solution["total_distance"] * 2.0  # 运输成本
                        + solution.get("total_late_minutes", 0) * 10.0,  # 迟到惩罚
                        "transport_cost": solution["total_distance"] * 2.0,
                        "labor_cost": 500.0,  # 固定人工成本
                        "fixed_cost": 300.0,  # 固定成本
                        "penalty_cost": solution.get("total_late_minutes", 0) * 10.0,
                        "carbon_emission_kg": solution["total_distance"] * 0.15,
                        "total_distance_km": solution["total_distance"],
                        "cost_breakdown": {
                            "运输成本": solution["total_distance"] * 2.0,
                            "人工成本": 500.0,
                            "固定成本": 300.0,
                            "惩罚成本": solution.get("total_late_minutes", 0) * 10.0,
                        },
                    }
                except Exception as e:
                    st.warning(f"成本计算失败: {e}")
                    cost_result = {
                        "total_cost": 0,
                        "transport_cost": 0,
                        "labor_cost": 0,
                        "fixed_cost": 0,
                        "penalty_cost": 0,
                        "carbon_emission_kg": 0,
                        "total_distance_km": 0,
                        "cost_breakdown": {},
                    }

                # 保存方案
                st.session_state.solutions_history.append(
                    {
                        "name": strategy_name,
                        "solution": solution,
                        "cost_result": cost_result,
                        "solve_time": solve_time,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

                progress_bar.progress((i + 1) / total)

            progress_bar.empty()
            status_text.empty()
            st.success(f"已完成 {total} 个方案的对比!")

    # 显示对比结果
    if st.session_state.solutions_history:
        st.markdown("---")

        # 汇总表格
        st.subheader("方案汇总")

        summary_data = []
        for sol in st.session_state.solutions_history:
            summary_data.append(
                {
                    "方案名称": sol["name"],
                    "求解状态": sol["solution"]["solution_status"],
                    "求解时间(秒)": f"{sol['solve_time']:.2f}",
                    "总距离(km)": f"{sol['solution']['total_distance']:.2f}",
                    "总成本(元)": f"¥{sol['cost_result']['total_cost']:,.2f}",
                    "碳排放(kg)": f"{sol['cost_result']['carbon_emission_kg']:.2f}",
                    "迟到(分钟)": sol["solution"].get("total_late_minutes", 0),
                }
            )

        df = pd.DataFrame(summary_data)
        st.dataframe(df)

        # 排序选择最佳方案
        if len(st.session_state.solutions_history) > 1:
            st.markdown("### 🏆 最佳方案推荐")

            # 按总成本排序
            sorted_solutions = sorted(
                st.session_state.solutions_history, key=lambda x: x["cost_result"]["total_cost"]
            )

            best = sorted_solutions[0]
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("最佳方案", best["name"])
            with col2:
                st.metric("总成本", f"¥{best['cost_result']['total_cost']:,.2f}")
            with col3:
                st.metric("总距离", f"{best['solution']['total_distance']:.2f} km")
            with col4:
                st.metric("求解时间", f"{best['solve_time']:.2f}s")

            # 加载最佳方案按钮
            if st.button("📥 加载最佳方案到主视图"):
                st.session_state.solution = {**best["solution"], "solution_name": best["name"]}
                st.session_state.cost_result = best["cost_result"]
                st.session_state.solve_time = best["solve_time"]
                st.success(f"已加载方案: {best['name']}")

        st.markdown("---")

        # 详细对比图表
        st.subheader("详细对比")

        tab1, tab2, tab3, tab4 = st.tabs(["成本对比", "性能对比", "路线对比", "碳排放对比"])

        with tab1:
            # 成本对比图
            names = [sol["name"] for sol in st.session_state.solutions_history]
            total_costs = [
                sol["cost_result"]["total_cost"] for sol in st.session_state.solutions_history
            ]
            transport_costs = [
                sol["cost_result"]["transport_cost"] for sol in st.session_state.solutions_history
            ]
            penalty_costs = [
                sol["cost_result"]["penalty_cost"] for sol in st.session_state.solutions_history
            ]

            fig = go.Figure()
            fig.add_trace(go.Bar(name="总成本", x=names, y=total_costs))
            fig.add_trace(go.Bar(name="运输成本", x=names, y=transport_costs))
            fig.add_trace(go.Bar(name="惩罚成本", x=names, y=penalty_costs))
            fig.update_layout(barmode="group", height=400)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            # 性能对比图
            solve_times = [sol["solve_time"] for sol in st.session_state.solutions_history]
            distances = [
                sol["solution"]["total_distance"] for sol in st.session_state.solutions_history
            ]

            fig = go.Figure()
            fig.add_trace(go.Bar(name="求解时间(秒)", x=names, y=solve_times))
            fig.add_trace(go.Bar(name="总距离(km)", x=names, y=distances))
            fig.update_layout(barmode="group", height=400)
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            # 路线数量对比
            vehicle_counts = []
            for sol in st.session_state.solutions_history:
                vehicle_counts.append(sum(sol["solution"]["vehicles_used"].values()))

            fig = go.Figure(
                data=[
                    go.Bar(
                        x=names,
                        y=vehicle_counts,
                        text=vehicle_counts,
                        textposition="auto",
                    )
                ]
            )
            fig.update_layout(
                title="各方案使用的车辆数量", xaxis_title="方案", yaxis_title="车辆数量", height=400
            )
            st.plotly_chart(fig, use_container_width=True)

            # 详细路线表
            for sol in st.session_state.solutions_history:
                with st.expander(f"📍 {sol['name']} - 路线详情"):
                    routes_data = []
                    for route in sol["solution"].get("routes", []):
                        customer_count = len(
                            [s for s in route.get("stops", []) if s.get("node", 0) > 0]
                        )
                        routes_data.append(
                            {
                                "车型": route.get("vehicle_type", ""),
                                "客户数": customer_count,
                                "距离(km)": round(route.get("distance_km", 0), 2),
                                "载重": route.get("total_demand", 0),
                            }
                        )
                    if routes_data:
                        st.dataframe(pd.DataFrame(routes_data), use_container_width=True)
                    else:
                        st.info("无路线数据")

        with tab4:
            # 碳排放对比
            carbon_emissions = [
                sol["cost_result"]["carbon_emission_kg"]
                for sol in st.session_state.solutions_history
            ]

            fig = go.Figure(
                data=[
                    go.Bar(
                        x=names,
                        y=carbon_emissions,
                        text=[f"{c:.2f} kg" for c in carbon_emissions],
                        textposition="auto",
                        marker_color=[
                            "#2ca02c" if c == min(carbon_emissions) else "#1f77b4"
                            for c in carbon_emissions
                        ],
                    )
                ]
            )
            fig.update_layout(
                title="各方案碳排放量对比",
                xaxis_title="方案",
                yaxis_title="碳排放量 (kg CO2)",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

            # 排序说明
            st.info("💡 绿色条表示碳排放最低的方案")


def main():
    """主函数。"""
    init_session_state()

    # 标题
    st.markdown('<h1 class="main-header">🚚 绿色物流路径优化引擎</h1>', unsafe_allow_html=True)
    st.markdown("---")

    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 求解参数")

        # 参数设置
        with st.expander("经济参数", expanded=True):
            fuel_price = st.number_input("油价 (元/升)", value=7.5, min_value=0.0, step=0.1)
            hourly_wage = st.number_input("时薪 (元/小时)", value=50.0, min_value=0.0, step=5.0)
            carbon_price = st.number_input("碳价 (元/kg)", value=0.08, min_value=0.0, step=0.01)
            late_penalty = st.number_input(
                "迟到罚金 (元/分钟)", value=10.0, min_value=0.0, step=1.0
            )

        with st.expander("求解器设置"):
            time_limit = st.slider("求解时间限制 (秒)", 10, 300, 60)
            use_multi_strategy = st.checkbox("多策略求解", value=True)

        st.markdown("---")

        # 车型配置
        st.header("🚛 车型配置")

        # 从会话状态加载或使用默认值
        if "vehicle_config" not in st.session_state:
            st.session_state.vehicle_config = DEFAULT_VEHICLE_CONFIG.copy()

        vehicle_config = {}
        with st.expander("4.2m 小型车"):
            c1 = st.number_input(
                "数量",
                value=st.session_state.vehicle_config["4.2m"]["count"],
                min_value=0,
                max_value=20,
                key="v1_count",
            )
            cap1 = st.number_input(
                "载重 (件)",
                value=st.session_state.vehicle_config["4.2m"]["capacity"],
                min_value=100,
                key="v1_cap",
            )
            vehicle_config["4.2m"] = {
                "capacity": cap1,
                "fixed_cost": 200,
                "fuel_per_100km": 12,
                "speed_kmh": 40,
                "count": c1,
                "color": "#1f77b4",
            }

        with st.expander("7.6m 中型车"):
            c2 = st.number_input(
                "数量",
                value=st.session_state.vehicle_config["7.6m"]["count"],
                min_value=0,
                max_value=20,
                key="v2_count",
            )
            cap2 = st.number_input(
                "载重 (件)",
                value=st.session_state.vehicle_config["7.6m"]["capacity"],
                min_value=100,
                key="v2_cap",
            )
            vehicle_config["7.6m"] = {
                "capacity": cap2,
                "fixed_cost": 350,
                "fuel_per_100km": 18,
                "speed_kmh": 35,
                "count": c2,
                "color": "#2ca02c",
            }

        with st.expander("9.6m 大型车"):
            c3 = st.number_input(
                "数量",
                value=st.session_state.vehicle_config["9.6m"]["count"],
                min_value=0,
                max_value=20,
                key="v3_count",
            )
            cap3 = st.number_input(
                "载重 (件)",
                value=st.session_state.vehicle_config["9.6m"]["capacity"],
                min_value=100,
                key="v3_cap",
            )
            vehicle_config["9.6m"] = {
                "capacity": cap3,
                "fixed_cost": 500,
                "fuel_per_100km": 25,
                "speed_kmh": 30,
                "count": c3,
                "color": "#9467bd",
            }

        # 保存车辆配置
        st.session_state.vehicle_config = vehicle_config

        st.markdown("---")

        # 操作按钮
        st.header("📋 操作")

        if st.button("📂 加载示例数据", use_container_width=True):
            st.session_state.customers_df = load_default_data()
            st.success(f"已加载 {len(st.session_state.customers_df)} 个节点")

        # 文件上传
        uploaded_file = st.file_uploader("上传客户数据 (CSV)", type=["csv"])
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                required_cols = [
                    "id",
                    "name",
                    "lat",
                    "lon",
                    "demand",
                    "service_time_min",
                    "tw_earliest",
                    "tw_latest",
                ]
                if all(col in df.columns for col in required_cols):
                    st.session_state.customers_df = df
                    st.success(f"已加载 {len(df)} 个节点")
                else:
                    missing = [col for col in required_cols if col not in df.columns]
                    st.error(f"缺少列: {missing}")
            except Exception as e:
                st.error(f"文件解析错误: {e}")

    # 主内容区
    tab1, tab2, tab3 = st.tabs(["🗺️ 地图可视化", "📊 成本分析", "📈 对比分析"])

    with tab1:
        # 客户数据预览
        if st.session_state.customers_df is not None:
            with st.expander("客户数据预览"):
                st.dataframe(st.session_state.customers_df, use_container_width=True)

        # 求解按钮
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            solve_button = st.button("🚀 开始求解", type="primary", use_container_width=True)

        # 执行求解
        if solve_button:
            if st.session_state.customers_df is None:
                st.warning("请先加载客户数据!")
            else:
                params = {
                    "fuel_price": fuel_price,
                    "hourly_wage": hourly_wage,
                    "carbon_price": carbon_price,
                    "late_penalty_per_min": late_penalty,
                    "search_time_limit": time_limit,
                    "use_multi_strategy": use_multi_strategy,
                }

                progress_bar = st.progress(0)
                status_text = st.empty()

                try:
                    status_text.text("正在初始化求解器...")
                    progress_bar.progress(10)

                    start_time = time.time()

                    # 创建求解器
                    solver = GreenVRPSolver(
                        customers_df=st.session_state.customers_df,
                        vehicle_config=vehicle_config,
                        time_penalty_per_min=late_penalty,
                        search_time_limit=time_limit,
                    )

                    status_text.text("正在求解最优路径...")
                    progress_bar.progress(30)

                    # 求解
                    if use_multi_strategy:
                        solution = solve_with_multiple_strategies(
                            customers_df=st.session_state.customers_df,
                            vehicle_config=vehicle_config,
                            time_penalty_per_min=late_penalty,
                            time_limit=time_limit,
                        )
                    else:
                        solution = solver.solve()

                    progress_bar.progress(80)

                    # 计算成本
                    status_text.text("正在计算成本...")
                    cost_result = calculate_green_cost(solution, vehicle_config, params)

                    progress_bar.progress(100)

                    solve_time = time.time() - start_time

                    # 保存结果
                    st.session_state.solution = solution
                    st.session_state.cost_result = cost_result
                    st.session_state.solve_time = solve_time

                    status_text.text(f"求解完成! 耗时: {solve_time:.2f}秒")

                except Exception as e:
                    st.error(f"求解失败: {e}")
                    progress_bar.empty()
                    status_text.empty()

        # 显示结果
        if st.session_state.solution:
            solution = st.session_state.solution

            # 状态指标
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("求解状态", solution.get("solution_status", "UNKNOWN"))
            with col2:
                st.metric("求解耗时", f"{st.session_state.solve_time:.2f}秒")
            with col3:
                st.metric("使用车辆", sum(solution.get("vehicles_used", {}).values()))
            with col4:
                st.metric("总迟到", f"{solution.get('total_late_minutes', 0)} 分钟")

            st.markdown("---")

            # 地图
            st.subheader("路线地图")
            m = create_map(st.session_state.customers_df, solution)
            st_folium(m, width=None, height=500, returned_objects=[])

            # 路线详情
            display_routes_table(solution)

            # 车辆使用
            display_vehicle_usage(solution, vehicle_config)

    with tab2:
        if st.session_state.cost_result:
            display_cost_analysis(st.session_state.cost_result, st.session_state.solution)
        else:
            st.info("请先进行求解以查看成本分析")

    with tab3:
        display_comparison_tab()

    # 页脚
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666;">
            <p>GreenVRP Engine v2.0 | 绿色物流路径优化引擎</p>
            <p>基于 OR-Tools 的异构车队 VRPTW 求解器 | 五维成本核算模型</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
