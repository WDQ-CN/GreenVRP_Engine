"""
GreenVRP Engine - Streamlit 主控入口（性能优化版 v2）

基于异构车队与软时间窗的城市配送碳排与成本优化系统。

功能模块：
1. 低碳路径规划 - 地图可视化与路线详情
2. 五维成本与碳排分析 - KPI 指标与成本结构图
3. 车辆作业甘特图 - 时间线可视化

性能优化 v2：
- 支持多策略求解模式
- 支持并行策略执行
- Streamlit数据缓存
- 成本效率分析
"""

from typing import Any, Dict

import numpy as np
import pandas as pd
import streamlit as st
from views import create_cost_stack_chart, create_gantt_chart, create_route_map

# 导入核心模块（性能优化版）
from core import (
    GreenVRPSolver,
    calculate_cost_efficiency_metrics,
    calculate_green_cost,
    solve_with_multiple_strategies,
)
from core.solver import solve_with_multiple_strategies_parallel

# ========== 页面配置 ==========
st.set_page_config(
    page_title="绿色路径优化引擎",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========== 全局参数默认值 ==========
DEFAULT_PARAMS = {
    "fuel_price": 7.5,  # 油价（元/升）
    "hourly_wage": 50.0,  # 时薪（元/小时）
    "carbon_price": 0.08,  # 碳交易价格（元/kg）
    "late_penalty_per_min": 10.0,  # 迟到罚金（元/分钟）
}

DEFAULT_VEHICLE_CONFIG = {
    "4.2m": {
        "capacity": 800,
        "fixed_cost": 200,
        "fuel_per_100km": 12,
        "speed_kmh": 40,
        "count": 3,
        "color": "#1f77b4",
    },
    "7.6m": {
        "capacity": 1500,
        "fixed_cost": 350,
        "fuel_per_100km": 18,
        "speed_kmh": 35,
        "count": 2,
        "color": "#2ca02c",
    },
    "9.6m": {
        "capacity": 2500,
        "fixed_cost": 500,
        "fuel_per_100km": 25,
        "speed_kmh": 30,
        "count": 2,
        "color": "#9467bd",
    },
}


@st.cache_data(ttl=3600)
def load_customers_data() -> pd.DataFrame:
    """
    加载客户数据（带缓存）。

    使用 Streamlit 缓存机制，避免每次交互都读取文件。
    缓存有效期为 1 小时。
    """
    try:
        df = pd.read_csv("data/mock_customers.csv")
        return df
    except FileNotFoundError:
        st.error("未找到客户数据文件 data/mock_customers.csv")
        return pd.DataFrame()


def render_sidebar() -> tuple:
    """
    渲染侧边栏参数配置。

    Returns:
        (params, vehicle_config, use_multi_strategy, use_parallel) 参数字典和求解策略选项
    """
    with st.sidebar:
        st.header("⚙️ 全局参数配置")

        # 求解策略配置（性能优化新增）
        st.subheader("🔬 求解策略")
        use_multi_strategy = st.checkbox(
            "启用多策略求解",
            value=True,
            help="尝试多种求解策略，返回最优解。适用于对解质量要求较高的场景。",
        )

        use_parallel = st.checkbox(
            "启用并行求解",
            value=True,
            help="并行执行多种策略，显著缩短求解时间（需要多核CPU）。",
        )

        search_time_limit = st.slider(
            "求解时间限制 (秒)",
            min_value=10,
            max_value=120,
            value=30,
            step=10,
            help="求解时间越长，解质量越好，但耗时更长。",
        )

        # 全局参数
        st.subheader("💰 经济参数")
        fuel_price = st.number_input(
            "油价 (元/升)",
            min_value=5.0,
            max_value=15.0,
            value=DEFAULT_PARAMS["fuel_price"],
            step=0.1,
        )
        hourly_wage = st.number_input(
            "时薪 (元/小时)",
            min_value=20.0,
            max_value=200.0,
            value=DEFAULT_PARAMS["hourly_wage"],
            step=5.0,
        )
        carbon_price = st.number_input(
            "碳交易价格 (元/kg)",
            min_value=0.01,
            max_value=1.0,
            value=DEFAULT_PARAMS["carbon_price"],
            step=0.01,
            format="%.2f",
        )
        late_penalty = st.number_input(
            "迟到罚金 (元/分钟)",
            min_value=1.0,
            max_value=100.0,
            value=DEFAULT_PARAMS["late_penalty_per_min"],
            step=1.0,
        )

        # 车型参数展示
        st.subheader("🚛 异构车队配置")
        for v_type, config in DEFAULT_VEHICLE_CONFIG.items():
            with st.expander(f"{v_type} 厢货", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("载重容量", f"{config['capacity']} 件")
                    st.metric("发车成本", f"¥{config['fixed_cost']}")
                with col2:
                    st.metric("百公里油耗", f"{config['fuel_per_100km']} L")
                    st.metric("平均速度", f"{config['speed_kmh']} km/h")

        params = {
            "fuel_price": fuel_price,
            "hourly_wage": hourly_wage,
            "carbon_price": carbon_price,
            "late_penalty_per_min": late_penalty,
            "search_time_limit": search_time_limit,
        }

        return params, DEFAULT_VEHICLE_CONFIG, use_multi_strategy, use_parallel


def render_route_table(routes: list) -> None:
    """
    渲染路线详情表格。

    包含时间戳和迟到警告。
    """
    if not routes:
        st.info("暂无路线数据")
        return

    for route in routes:
        vehicle_id = route["vehicle_id"]
        vehicle_type = route["vehicle_type"]
        stops = [s for s in route["stops"] if s.get("node", 0) > 0]

        if not stops:
            continue

        # 创建表格数据
        table_data = []
        for stop in stops:
            arrival = stop.get("arrival_time", 0)
            tw_earliest = stop.get("tw_earliest", 0)
            tw_latest = stop.get("tw_latest", 0)
            late_minutes = stop.get("late_minutes", 0)
            is_late = stop.get("is_late", False)

            # 格式化时间
            arrival_str = _format_time(arrival)
            tw_str = f"{_format_time(tw_earliest)} - {_format_time(tw_latest)}"

            # 迟到警告
            status = "✅ 正常" if not is_late else f"⚠️ 迟到 {late_minutes}分钟"

            table_data.append(
                {
                    "客户": stop.get("customer_name", ""),
                    "需求量": f"{stop.get('demand', 0)} 件",
                    "到达时间": arrival_str,
                    "时间窗": tw_str,
                    "状态": status,
                }
            )

        df = pd.DataFrame(table_data)

        # 显示表格
        st.subheader(f"🚚 车辆 {vehicle_id + 1} ({vehicle_type})")
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )


def _format_time(minutes: int) -> str:
    """将分钟数转换为 HH:MM 格式。"""
    hours = (minutes // 60) % 24
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def render_kpi_cards(cost_result: Dict[str, Any], solution: Dict[str, Any]) -> None:
    """
    渲染五维成本 KPI 指标卡。

    突出显示碳排放量及碳排成本。
    """
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "💰 总成本",
            f"¥{cost_result['total_cost']:,.0f}",
        )

    with col2:
        st.metric(
            "🚚 运输成本",
            f"¥{cost_result['transport_cost']:,.0f}",
        )

    with col3:
        st.metric(
            "👥 人工成本",
            f"¥{cost_result['labor_cost']:,.0f}",
        )

    with col4:
        # 碳排放 - 突出显示
        st.metric(
            "🌿 碳排放量",
            f"{cost_result['carbon_emission_kg']:,.1f} kg",
            delta="CO2",
            delta_color="off",
        )

    with col5:
        # 碳排成本 - 突出显示
        st.metric(
            "♻️ 碳排成本",
            f"¥{cost_result['carbon_cost']:,.2f}",
        )

    # 性能指标（第二行）
    st.divider()
    col6, col7, col8, col9 = st.columns(4)

    with col6:
        solve_time = solution.get("solve_time_seconds", 0)
        st.metric(
            "⏱️ 求解耗时",
            f"{solve_time:.2f} 秒",
        )

    with col7:
        st.metric(
            "📏 总距离",
            f"{cost_result['total_distance_km']:,.1f} km",
        )

    with col8:
        st.metric(
            "⏰ 总时间",
            f"{cost_result['total_time_min']:,.0f} 分钟",
        )

    with col9:
        late_minutes = solution.get("total_late_minutes", 0)
        st.metric(
            "⚠️ 迟到时间",
            f"{late_minutes} 分钟",
            delta="惩罚成本" if late_minutes > 0 else "准时配送",
            delta_color="inverse" if late_minutes > 0 else "normal",
        )


def render_efficiency_metrics(cost_result: Dict[str, Any], solution: Dict[str, Any]) -> None:
    """
    渲染成本效率指标（性能优化新增）。

    用于评估物流运营效率。
    """
    efficiency = calculate_cost_efficiency_metrics(cost_result, solution)

    st.subheader("📊 效率指标")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "单位距离成本",
            f"¥{efficiency['cost_per_km']}/km",
        )

    with col2:
        st.metric(
            "单位客户成本",
            f"¥{efficiency['cost_per_customer']}/客户",
        )

    with col3:
        st.metric(
            "单位距离碳排放",
            f"{efficiency['carbon_per_km']:.4f} kg/km",
        )

    with col4:
        st.metric(
            "人工效率",
            f"{efficiency['labor_efficiency']*100:.1f}%",
            help="服务时间占总时间的比例",
        )


def main():
    """主函数：Streamlit 应用入口。"""
    # 标题
    st.title("🌿 绿色物流路径优化引擎")
    st.markdown("### 基于异构车队与软时间窗的城市配送碳排与成本优化系统")

    st.divider()

    # 加载侧边栏参数
    params, vehicle_config, use_multi_strategy, use_parallel = render_sidebar()

    # 加载客户数据
    customers_df = load_customers_data()

    if customers_df.empty:
        st.warning("请确保 data/mock_customers.csv 文件存在")
        return

    # 显示数据预览
    with st.expander("📊 客户数据预览", expanded=False):
        st.dataframe(customers_df, use_container_width=True, hide_index=True)

    # 求解按钮
    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_center:
        solve_button = st.button("🚀 开始求解", type="primary", use_container_width=True)

    if solve_button:
        with st.spinner("正在求解最优路径..."):
            # 根据策略选择求解方式
            if use_multi_strategy and use_parallel:
                # 并行多策略求解（性能最优）
                try:
                    solution = solve_with_multiple_strategies_parallel(
                        customers_df=customers_df,
                        vehicle_config=vehicle_config,
                        time_penalty_per_min=params["late_penalty_per_min"],
                        time_limit=params["search_time_limit"],
                    )
                except Exception as e:
                    st.warning(f"并行求解失败，回退到串行模式: {e}")
                    solution = solve_with_multiple_strategies(
                        customers_df=customers_df,
                        vehicle_config=vehicle_config,
                        time_penalty_per_min=params["late_penalty_per_min"],
                        time_limit=params["search_time_limit"],
                    )
            elif use_multi_strategy:
                # 串行多策略求解
                solution = solve_with_multiple_strategies(
                    customers_df=customers_df,
                    vehicle_config=vehicle_config,
                    time_penalty_per_min=params["late_penalty_per_min"],
                    time_limit=params["search_time_limit"],
                )
            else:
                # 单策略求解
                solver = GreenVRPSolver(
                    customers_df=customers_df,
                    vehicle_config=vehicle_config,
                    time_penalty_per_min=params["late_penalty_per_min"],
                    search_time_limit=params["search_time_limit"],
                )
                solution = solver.solve()

            # 计算成本
            cost_result = calculate_green_cost(solution, vehicle_config, params)

            # 存储到 session state
            st.session_state["solution"] = solution
            st.session_state["cost_result"] = cost_result

    # 检查是否有求解结果
    if "solution" not in st.session_state:
        st.info("👆 点击「开始求解」按钮进行路径优化")
        return

    solution = st.session_state["solution"]
    cost_result = st.session_state["cost_result"]

    # 检查求解状态
    if solution.get("solution_status") != "SUCCESS":
        st.error(f"求解失败: {solution.get('solution_status', 'Unknown')}")
        return

    # ========== Tab 布局 ==========
    tab1, tab2, tab3 = st.tabs(
        [
            "🗺️ 低碳路径规划",
            "💰 五维成本与碳排分析",
            "⏱️ 车辆作业甘特图",
        ]
    )

    # Tab 1: 地图与路线表
    with tab1:
        st.subheader("📍 配送路线地图")

        # 创建地图
        route_map = create_route_map(solution, customers_df)
        st.components.v1.html(
            route_map._repr_html_(),
            height=500,
        )

        st.divider()

        # 路线详情表格
        st.subheader("📋 路线详情")
        render_route_table(solution.get("routes", []))

    # Tab 2: 成本分析
    with tab2:
        st.subheader("📊 五维成本 KPI")
        render_kpi_cards(cost_result, solution)

        st.divider()

        # 成本效率指标（性能优化新增）
        render_efficiency_metrics(cost_result, solution)

        st.divider()

        # 成本结构图
        col_chart, col_info = st.columns([2, 1])

        with col_chart:
            st.subheader("📈 成本结构分析")
            cost_chart = create_cost_stack_chart(cost_result)
            st.plotly_chart(cost_chart, use_container_width=True)

        with col_info:
            st.subheader("📝 成本明细")
            for name, value in cost_result["cost_breakdown"].items():
                st.write(f"**{name}:** ¥{value:,.2f}")

            st.divider()

            st.subheader("🚛 车辆使用情况")
            vehicles_used = solution.get("vehicles_used", {})
            for v_type, count in vehicles_used.items():
                st.write(f"**{v_type} 厢货:** {count} 辆")

            st.divider()

            st.subheader("⏰ 时间分解")
            st.write(f"**行驶时间:** {cost_result['driving_time_min']:,.1f} 分钟")
            st.write(f"**服务时间:** {cost_result['service_time_min']:,.1f} 分钟")
            st.write(f"**等待时间:** {cost_result['waiting_time_min']:,.1f} 分钟")

    # Tab 3: 甘特图
    with tab3:
        st.subheader("📅 车辆作业时间线")

        gantt_chart = create_gantt_chart(solution, vehicle_config)
        st.plotly_chart(gantt_chart, use_container_width=True)

        # 图例说明
        st.markdown("""
        **图例说明:**
        - 🔵 **行驶** - 车辆行驶中
        - 🟢 **服务** - 客户卸货
        - 🟡 **等待** - 早到等待
        - 🔴 **迟到** - 迟到警告
        """)


if __name__ == "__main__":
    main()
