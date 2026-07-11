"""
GreenVRP Engine - Enterprise Simplified UI
企业简约风格的前端界面
"""

import os
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.vehicles import DEFAULT_VEHICLE_CONFIG
from core.cost import calculate_green_cost
from core.solver import GreenVRPSolver, solve_with_multiple_strategies

# ========== 企业简约风格配色系统 ==========
ENTERPRISE_COLORS = {
    "primary": "#2C3E50",  # 深蓝灰 - 主色
    "secondary": "#34495E",  # 中蓝灰 - 次要色
    "accent": "#3498DB",  # 科技蓝 - 强调色
    "success": "#27AE60",  # 成功绿
    "warning": "#F39C12",  # 警告橙
    "danger": "#E74C3C",  # 危险红
    "light": "#ECF0F1",  # 浅灰背景
    "white": "#FFFFFF",  # 白色
    "gray": "#95A5A6",  # 灰色文字
    "dark_gray": "#7F8C8D",  # 深灰
}

# ========== 页面配置 ==========
st.set_page_config(
    page_title="绿色物流路径优化引擎",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ========== 自定义 CSS 样式 ==========
def load_enterprise_styles():
    """加载企业简约风格的 CSS 样式"""
    st.markdown(
        f"""
    <style>
        /* 全局样式重置 */
        .main {{
            background-color: {ENTERPRISE_COLORS['light']};
        }}

        /* 主标题样式 */
        .enterprise-header {{
            text-align: center;
            padding: 2rem 0;
            border-bottom: 2px solid {ENTERPRISE_COLORS['primary']};
            margin-bottom: 2rem;
        }}

        .enterprise-title {{
            font-size: 2rem;
            font-weight: 600;
            color: {ENTERPRISE_COLORS['primary']};
            margin: 0;
            letter-spacing: 0.5px;
        }}

        .enterprise-subtitle {{
            font-size: 1rem;
            color: {ENTERPRISE_COLORS['gray']};
            margin-top: 0.5rem;
            font-weight: 400;
        }}

        /* 卡片样式 */
        .enterprise-card {{
            background-color: {ENTERPRISE_COLORS['white']};
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border: 1px solid #E8E8E8;
            margin-bottom: 1rem;
        }}

        /* 指标卡片样式 */
        .metric-card {{
            background-color: {ENTERPRISE_COLORS['white']};
            border-radius: 6px;
            padding: 1.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            border: 1px solid #E8E8E8;
            transition: all 0.3s ease;
        }}

        .metric-card:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.12);
            transform: translateY(-2px);
        }}

        .metric-title {{
            font-size: 0.875rem;
            color: {ENTERPRISE_COLORS['gray']};
            margin-bottom: 0.5rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .metric-value {{
            font-size: 1.75rem;
            font-weight: 600;
            color: {ENTERPRISE_COLORS['primary']};
            line-height: 1.2;
        }}

        .metric-delta {{
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }}

        .metric-delta.positive {{
            color: {ENTERPRISE_COLORS['success']};
        }}

        .metric-delta.negative {{
            color: {ENTERPRISE_COLORS['danger']};
        }}

        /* 按钮样式 */
        .stButton>button {{
            background-color: {ENTERPRISE_COLORS['primary']};
            color: {ENTERPRISE_COLORS['white']};
            border: none;
            border-radius: 4px;
            padding: 0.625rem 1.25rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }}

        .stButton>button:hover {{
            background-color: {ENTERPRISE_COLORS['secondary']};
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        /* 侧边栏样式 */
        [data-testid="stSidebar"] {{
            background-color: {ENTERPRISE_COLORS['white']};
            border-right: 1px solid #E8E8E8;
        }}

        /* 标签页样式 */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0;
        }}

        .stTabs [data-baseweb="tab"] {{
            background-color: {ENTERPRISE_COLORS['white']};
            color: {ENTERPRISE_COLORS['gray']};
            border: none;
            border-bottom: 2px solid transparent;
            padding: 0.75rem 1.5rem;
            font-weight: 500;
        }}

        .stTabs [aria-selected="true"] {{
            color: {ENTERPRISE_COLORS['primary']};
            border-bottom: 2px solid {ENTERPRISE_COLORS['accent']};
        }}

        /* 数据表格样式 */
        .dataframe {{
            border: 1px solid #E8E8E8;
            border-radius: 4px;
            overflow: hidden;
        }}

        /* 进度条样式 */
        .stProgress > div > div > div {{
            background-color: {ENTERPRISE_COLORS['accent']};
        }}

        /* 分隔线样式 */
    hr {{
        border: none;
        border-top: 1px solid #E8E8E8;
            margin: 1.5rem 0;
        }}

        /* 状态标签样式 */
        .status-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }}

        .status-badge.success {{
            background-color: rgba(39, 174, 96, 0.1);
            color: {ENTERPRISE_COLORS['success']};
        }}

        .status-badge.warning {{
            background-color: rgba(243, 156, 18, 0.1);
            color: {ENTERPRISE_COLORS['warning']};
        }}

        .status-badge.error {{
            background-color: rgba(231, 76, 60, 0.1);
            color: {ENTERPRISE_COLORS['danger']};
        }}

        /* 章节标题样式 */
        .section-header {{
            color: {ENTERPRISE_COLORS['primary']};
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid {ENTERPRISE_COLORS['accent']};
        }}

        /* 页脚样式 */
        .enterprise-footer {{
            text-align: center;
            padding: 2rem 0;
            color: {ENTERPRISE_COLORS['gray']};
            font-size: 0.875rem;
            border-top: 1px solid #E8E8E8;
            margin-top: 2rem;
        }}

        /* 输入框样式 */
        .stNumberInput > div > div > input {{
            border: 1px solid #E8E8E8;
            border-radius: 4px;
        }}

        /* 展开器样式 */
        .streamlit-expanderHeader {{
            background-color: {ENTERPRISE_COLORS['white']};
            border: 1px solid #E8E8E8;
            border-radius: 4px;
        }}
    </style>
    """,
        unsafe_allow_html=True,
    )


# ========== 会话状态初始化 ==========
def init_session_state():
    """初始化会话状态"""
    state_defaults = {
        "solution": None,
        "cost_result": None,
        "customers_df": None,
        "solve_time": 0,
        "vehicle_config": DEFAULT_VEHICLE_CONFIG.copy(),
        "solutions_history": [],
        "current_solution_name": None,
    }

    for key, default_value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


# ========== 企业风格组件 ==========
def enterprise_header(title: str, subtitle: str = ""):
    """企业风格的主标题组件"""
    st.markdown(
        f"""
    <div class="enterprise-header">
        <h1 class="enterprise-title">{title}</h1>
        <p class="enterprise-subtitle">{subtitle}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def enterprise_metric_card(title: str, value: str, delta: str = "", delta_type: str = "neutral"):
    """企业风格的指标卡片组件"""
    delta_class = ""
    if delta_type == "positive":
        delta_class = "positive"
    elif delta_type == "negative":
        delta_class = "negative"

    delta_html = ""
    if delta:
        delta_html = f'<div class="metric-delta {delta_class}">{delta}</div>'

    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """,
        unsafe_allow_html=True,
    )


def enterprise_section_header(title: str):
    """企业风格的章节标题"""
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def enterprise_status_badge(text: str, status: str = "success"):
    """企业风格的状态标签"""
    st.markdown(f'<span class="status-badge {status}">{text}</span>', unsafe_allow_html=True)


# ========== 数据加载函数 ==========
def load_default_data():
    """加载默认客户数据"""
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


# ========== 侧边栏渲染 ==========
def render_enterprise_sidebar():
    """渲染企业风格的侧边栏"""
    with st.sidebar:
        st.markdown("### ⚙️ 求解参数")
        st.markdown("---")

        # 经济参数
        with st.expander("💰 经济参数", expanded=True):
            fuel_price = st.number_input(
                "油价 (元/升)", value=7.5, min_value=0.0, step=0.1, format="%.2f"
            )
            hourly_wage = st.number_input(
                "时薪 (元/小时)", value=50.0, min_value=0.0, step=5.0, format="%.2f"
            )
            carbon_price = st.number_input(
                "碳价 (元/kg)", value=0.08, min_value=0.0, step=0.01, format="%.3f"
            )
            late_penalty = st.number_input(
                "迟到罚金 (元/分钟)", value=10.0, min_value=0.0, step=1.0, format="%.2f"
            )

        # 求解器设置
        with st.expander("🔧 求解器设置"):
            time_limit = st.slider(
                "求解时间限制 (秒)", min_value=10, max_value=300, value=60, step=10
            )
            use_multi_strategy = st.checkbox(
                "多策略求解", value=True, help="启用多种求解策略以获得更优解"
            )

        st.markdown("---")
        st.markdown("### 🚛 车型配置")

        # 车型配置
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
                "color": ENTERPRISE_COLORS["accent"],
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
                "color": ENTERPRISE_COLORS["success"],
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
                "color": ENTERPRISE_COLORS["primary"],
            }

        # 保存车辆配置
        st.session_state.vehicle_config = vehicle_config

        st.markdown("---")
        st.markdown("### 📋 数据管理")

        # 数据加载按钮
        if st.button("📂 加载示例数据", use_container_width=True):
            st.session_state.customers_df = load_default_data()
            st.success(f"已加载 {len(st.session_state.customers_df)} 个节点")

        # 文件上传
        uploaded_file = st.file_uploader(
            "上传客户数据 (CSV)",
            type=["csv"],
            help="请包含以下列: id, name, lat, lon, demand, service_time_min, tw_earliest, tw_latest",
        )

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

    return {
        "fuel_price": fuel_price,
        "hourly_wage": hourly_wage,
        "carbon_price": carbon_price,
        "late_penalty_per_min": late_penalty,
        "search_time_limit": time_limit,
        "use_multi_strategy": use_multi_strategy,
        "vehicle_config": vehicle_config,
    }


# ========== 主内容区 ==========
def render_dashboard():
    """渲染主仪表板"""

    # 数据预览
    if st.session_state.customers_df is not None:
        with st.expander("📊 客户数据预览", expanded=False):
            st.dataframe(st.session_state.customers_df, use_container_width=True, hide_index=True)

    # 求解按钮区域
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        solve_button = st.button(
            "🚀 开始求解", type="primary", use_container_width=True, use_container_height=True
        )

    # 执行求解
    if solve_button:
        if st.session_state.customers_df is None:
            st.warning("请先加载客户数据!")
        else:
            execute_solve()


# ========== 求解执行 ==========
def execute_solve():
    """执行求解过程"""
    params = {
        "fuel_price": st.session_state.get("fuel_price", 7.5),
        "hourly_wage": st.session_state.get("hourly_wage", 50.0),
        "carbon_price": st.session_state.get("carbon_price", 0.08),
        "late_penalty_per_min": st.session_state.get("late_penalty_per_min", 10.0),
        "search_time_limit": st.session_state.get("search_time_limit", 60),
    }

    use_multi_strategy = st.session_state.get("use_multi_strategy", True)
    vehicle_config = st.session_state.vehicle_config

    with st.container():
        progress_bar = st.progress(0)
        status_placeholder = st.empty()

        try:
            status_placeholder.text("正在初始化求解器...")
            progress_bar.progress(10)

            start_time = time.time()

            # 创建求解器
            solver = GreenVRPSolver(
                customers_df=st.session_state.customers_df,
                vehicle_config=vehicle_config,
                time_penalty_per_min=params["late_penalty_per_min"],
                search_time_limit=params["search_time_limit"],
            )

            status_placeholder.text("正在求解最优路径...")
            progress_bar.progress(30)

            # 求解
            if use_multi_strategy:
                solution = solve_with_multiple_strategies(
                    customers_df=st.session_state.customers_df,
                    vehicle_config=vehicle_config,
                    time_penalty_per_min=params["late_penalty_per_min"],
                    time_limit=params["search_time_limit"],
                )
            else:
                solution = solver.solve()

            progress_bar.progress(70)

            # 计算成本
            status_placeholder.text("正在计算成本...")
            cost_result = calculate_green_cost(solution, vehicle_config, params)

            progress_bar.progress(90)

            solve_time = time.time() - start_time

            # 保存结果
            st.session_state.solution = solution
            st.session_state.cost_result = cost_result
            st.session_state.solve_time = solve_time

            progress_bar.progress(100)
            status_placeholder.empty()

            st.success(f"求解完成! 耗时: {solve_time:.2f}秒")

        except Exception as e:
            st.error(f"求解失败: {str(e)}")
            progress_bar.empty()
            status_placeholder.empty()


# ========== 结果展示 ==========
def render_results():
    """渲染求解结果"""
    if not st.session_state.solution:
        st.info("请先进行求解以查看结果")
        return

    solution = st.session_state.solution
    cost_result = st.session_state.cost_result

    # 检查求解状态
    if solution.get("solution_status") != "SUCCESS":
        st.error(f"求解失败: {solution.get('solution_status', 'Unknown')}")
        return

    # 显示状态指标
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        enterprise_metric_card("求解状态", "成功", "Status: SUCCESS")

    with col2:
        enterprise_metric_card("求解耗时", f"{st.session_state.solve_time:.2f}s", f"Performance")

    with col3:
        vehicles_used = sum(solution.get("vehicles_used", {}).values())
        enterprise_metric_card("使用车辆", f"{vehicles_used} 辆", f"Fleet Utilization")

    with col4:
        late_minutes = solution.get("total_late_minutes", 0)
        delta_type = "negative" if late_minutes > 0 else "positive"
        delta_text = f"迟到 {late_minutes}分钟" if late_minutes > 0 else "准时配送"
        enterprise_metric_card("总迟到时间", f"{late_minutes}分钟", delta_text, delta_type)

    st.markdown("---")


# ========== 主函数 ==========
def main():
    """主函数"""
    # 加载样式
    load_enterprise_styles()

    # 初始化会话状态
    init_session_state()

    # 企业风格标题
    enterprise_header(
        "绿色物流路径优化引擎", "Enterprise Green Logistics Route Optimization Engine"
    )

    # 渲染侧边栏
    sidebar_params = render_enterprise_sidebar()

    # 存储参数到会话状态
    st.session_state.update(sidebar_params)

    # 主标签页
    tab1, tab2, tab3 = st.tabs(["📊 仪表板", "🗺️ 路线规划", "💰 成本分析"])

    with tab1:
        render_dashboard()
        render_results()

    with tab2:
        if st.session_state.solution:
            enterprise_section_header("路线规划结果")
            st.info("路线规划视图正在开发中...")
        else:
            st.info("请先进行求解以查看路线规划")

    with tab3:
        if st.session_state.cost_result:
            enterprise_section_header("成本分析")
            render_cost_analysis()
        else:
            st.info("请先进行求解以查看成本分析")

    # 页脚
    st.markdown(
        f"""
    <div class="enterprise-footer">
        <p>GreenVRP Engine Enterprise Edition</p>
        <p>© 2024 绿色物流路径优化引擎 | 基于异构车队与软时间窗的城市配送碳排与成本优化系统</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_cost_analysis():
    """渲染成本分析"""
    cost_result = st.session_state.cost_result
    solution = st.session_state.solution

    # 主要指标卡
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        enterprise_metric_card("总成本", f"¥{cost_result['total_cost']:,.0f}", "Total Cost")

    with col2:
        enterprise_metric_card(
            "运输成本", f"¥{cost_result['transport_cost']:,.0f}", "Transport Cost"
        )

    with col3:
        enterprise_metric_card("人工成本", f"¥{cost_result['labor_cost']:,.0f}", "Labor Cost")

    with col4:
        enterprise_metric_card(
            "碳排放量", f"{cost_result['carbon_emission_kg']:,.1f} kg", "Carbon Emission"
        )

    with col5:
        enterprise_metric_card("碳排成本", f"¥{cost_result['carbon_cost']:,.2f}", "Carbon Cost")

    st.markdown("---")

    # 性能指标
    col6, col7, col8, col9 = st.columns(4)

    with col6:
        solve_time = solution.get("solve_time_seconds", 0)
        enterprise_metric_card("求解耗时", f"{solve_time:.2f}s", "Solve Time")

    with col7:
        enterprise_metric_card(
            "总距离", f"{cost_result['total_distance_km']:,.1f}km", "Total Distance"
        )

    with col8:
        enterprise_metric_card("总时间", f"{cost_result['total_time_min']:,.0f}分钟", "Total Time")

    with col9:
        late_minutes = solution.get("total_late_minutes", 0)
        delta_type = "negative" if late_minutes > 0 else "positive"
        enterprise_metric_card(
            "迟到时间",
            f"{late_minutes}分钟",
            "Late Delivery" if late_minutes > 0 else "On Time",
            delta_type,
        )

    st.markdown("---")

    # 成本明细表
    enterprise_section_header("成本明细")

    total_cost = cost_result["total_cost"]
    cost_data = []
    for name, value in cost_result["cost_breakdown"].items():
        percentage = (value / total_cost * 100) if total_cost > 0 else 0
        cost_data.append({"项目": name, "金额": f"¥{value:,.2f}", "占比": f"{percentage:.1f}%"})

    cost_df = pd.DataFrame(cost_data)
    st.dataframe(cost_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 车辆使用情况
    enterprise_section_header("车辆使用情况")

    vehicles_used = solution.get("vehicles_used", {})
    vehicle_data = []
    for v_type, count in vehicles_used.items():
        vehicle_data.append(
            {
                "车型": v_type,
                "使用数量": count,
                "配置": f"{st.session_state.vehicle_config[v_type]['capacity']}件载重",
            }
        )

    vehicle_df = pd.DataFrame(vehicle_data)
    st.dataframe(vehicle_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 时间分解
    enterprise_section_header("时间分解")

    col1, col2, col3 = st.columns(3)

    with col1:
        enterprise_metric_card(
            "行驶时间", f"{cost_result['driving_time_min']:,.1f}分钟", "Driving Time"
        )

    with col2:
        enterprise_metric_card(
            "服务时间", f"{cost_result['service_time_min']:,.1f}分钟", "Service Time"
        )

    with col3:
        enterprise_metric_card(
            "等待时间", f"{cost_result['waiting_time_min']:,.1f}分钟", "Waiting Time"
        )


if __name__ == "__main__":
    main()
