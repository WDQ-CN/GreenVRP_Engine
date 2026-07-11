"""
前端配置文件
"""

# ========== 企业配色方案 ==========
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

# ========== 图表配置 ==========
CHART_CONFIG = {
    "font": {"family": "Arial, sans-serif", "size": 12, "color": ENTERPRISE_COLORS["primary"]},
    "paper_bgcolor": "white",
    "plot_bgcolor": "white",
    "margin": dict(l=10, r=10, t=10, b=10),
    "xaxis": {
        "gridcolor": ENTERPRISE_COLORS["light"],
        "zerolinecolor": ENTERPRISE_COLORS["light"],
    },
    "yaxis": {
        "gridcolor": ENTERPRISE_COLORS["light"],
        "zerolinecolor": ENTERPRISE_COLORS["light"],
    },
}

# ========== 页面配置 ==========
PAGE_CONFIG = {
    "page_title": "绿色物流路径优化引擎",
    "page_icon": "🚚",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# ========== 默认参数 ==========
DEFAULT_PARAMS = {
    "fuel_price": 7.5,  # 油价（元/升）
    "hourly_wage": 50.0,  # 时薪（元/小时）
    "carbon_price": 0.08,  # 碳交易价格（元/kg）
    "late_penalty_per_min": 10.0,  # 迟到罚金（元/分钟）
    "search_time_limit": 60,  # 求解时间限制（秒）
}

# ========== 车辆配置 ==========
DEFAULT_VEHICLE_CONFIG = {
    "4.2m": {
        "capacity": 800,
        "fixed_cost": 200,
        "fuel_per_100km": 12,
        "speed_kmh": 40,
        "count": 3,
        "color": ENTERPRISE_COLORS["accent"],
        "name": "小型厢货",
    },
    "7.6m": {
        "capacity": 1500,
        "fixed_cost": 350,
        "fuel_per_100km": 18,
        "speed_kmh": 35,
        "count": 2,
        "color": ENTERPRISE_COLORS["success"],
        "name": "中型厢货",
    },
    "9.6m": {
        "capacity": 2500,
        "fixed_cost": 500,
        "fuel_per_100km": 25,
        "speed_kmh": 30,
        "count": 2,
        "color": ENTERPRISE_COLORS["primary"],
        "name": "大型厢货",
    },
}

# ========== 求解策略配置 ==========
STRATEGY_CONFIG = {
    "multi_strategy": {
        "name": "多策略最优",
        "description": "尝试多种策略组合，选择最优解",
        "enabled": True,
    },
    "parallel_solving": {
        "name": "并行求解",
        "description": "并行执行多种策略，显著缩短求解时间",
        "enabled": True,
    },
    "strategies": {
        "guided_local_search": {
            "name": "引导局部搜索",
            "description": "使用引导局部搜索算法",
            "first_solution": "PATH_CHEAPEST_ARC",
            "metaheuristic": "GUIDED_LOCAL_SEARCH",
        },
        "tabu_search": {
            "name": "禁忌搜索",
            "description": "使用禁忌搜索算法",
            "first_solution": "PATH_CHEAPEST_ARC",
            "metaheuristic": "TABU_SEARCH",
        },
        "simulated_annealing": {
            "name": "模拟退火",
            "description": "使用模拟退火算法",
            "first_solution": "AUTOMATIC",
            "metaheuristic": "SIMULATED_ANNEALING",
        },
        "savings": {
            "name": "节约算法",
            "description": "使用节约算法构造初始解",
            "first_solution": "SAVINGS",
            "metaheuristic": "GUIDED_LOCAL_SEARCH",
        },
        "sweep": {
            "name": "扫帚算法",
            "description": "使用扫帚算法构造初始解",
            "first_solution": "SWEEP",
            "metaheuristic": "GUIDED_LOCAL_SEARCH",
        },
    },
}

# ========== 地图配置 ==========
MAP_CONFIG = {
    "default_center": {"lat": 39.9042, "lon": 116.4074},  # 北京
    "default_zoom": 12,
    "tiles": "OpenStreetMap",
    "marker_styles": {
        "warehouse": {"color": "darkred", "icon": "warehouse", "prefix": "fa"},
        "customer": {"radius": 10, "fill_opacity": 0.3, "weight": 2},
        "late_customer": {"color": ENTERPRISE_COLORS["warning"]},
    },
    "route_styles": {"width": 3, "opacity": 0.7},
}

# ========== 性能配置 ==========
PERFORMANCE_CONFIG = {
    "cache_ttl": 3600,  # 缓存时间（秒）
    "max_history_size": 10,  # 最大历史记录数
    "progress_bar_steps": 5,  # 进度条步数
}

# ========== 语言配置 ==========
LANGUAGE_CONFIG = {
    "zh": {
        "app_title": "绿色物流路径优化引擎",
        "app_subtitle": "Enterprise Green Logistics Route Optimization Engine",
        "sidebar_title": "⚙️ 求解参数",
        "vehicle_config_title": "🚛 车型配置",
        "data_management_title": "📋 数据管理",
        "dashboard": "📊 仪表板",
        "route_planning": "🗺️ 路线规划",
        "cost_analysis": "💰 成本分析",
        "comparison_analysis": "📈 对比分析",
        "solve_button": "🚀 开始求解",
        "load_data_button": "📂 加载示例数据",
    },
    "en": {
        "app_title": "Green Logistics Route Optimization Engine",
        "app_subtitle": "Enterprise Green Logistics Route Optimization Engine",
        "sidebar_title": "⚙️ Solver Parameters",
        "vehicle_config_title": "🚛 Vehicle Configuration",
        "data_management_title": "📋 Data Management",
        "dashboard": "📊 Dashboard",
        "route_planning": "🗺️ Route Planning",
        "cost_analysis": "💰 Cost Analysis",
        "comparison_analysis": "📈 Comparison Analysis",
        "solve_button": "🚀 Start Solving",
        "load_data_button": "📂 Load Sample Data",
    },
}

# ========== 当前语言设置 ==========
CURRENT_LANGUAGE = "zh"


def get_text(key):
    """
    根据键获取本地化文本

    Args:
        key: 文本键

    Returns:
        str: 本地化文本
    """
    return LANGUAGE_CONFIG[CURRENT_LANGUAGE].get(key, key)
