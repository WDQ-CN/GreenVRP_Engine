"""
物理常量和默认参数模块

统一管理物理常量和默认计算参数。
"""

from typing import Dict

# ==================== 物理常量 ====================

# 地球半径（公里）
EARTH_RADIUS_KM: float = 6371.0

# 柴油碳排放因子（kg CO2 / 升）
DIESEL_CO2_FACTOR: float = 2.63

# 不同车型的碳排放基线（kg CO2 / km）
VEHICLE_CARBON_BASELINE: Dict[str, float] = {
    "4.2m": 8.0,
    "7.6m": 12.0,
    "9.6m": 16.0,
}


# ==================== 默认参数 ====================

# 默认全局参数
DEFAULT_PARAMS: Dict[str, float] = {
    "fuel_price": 7.5,  # 油价（元/升）
    "hourly_wage": 50.0,  # 时薪（元/小时）
    "carbon_price": 0.08,  # 碳价（元/kg CO2）
    "late_penalty_per_min": 10.0,  # 迟到罚金（元/分钟）
    "waiting_cost_per_min": 5.0,  # 等待成本（元/分钟）
}


# ==================== 时间常量 ====================

# 工作时间常量（分钟）
WORK_DAY_START_MIN: int = 480  # 8:00
WORK_DAY_END_MIN: int = 1080  # 18:00
DEFAULT_SERVICE_TIME_MIN: float = 15.0


# ==================== 求解器常量 ====================

# 默认求解时间限制（秒）
DEFAULT_TIME_LIMIT_SECONDS: int = 60

# 求解策略
SOLVER_STRATEGIES = {
    "fast": {"time_limit": 30, "description": "快速求解"},
    "balanced": {"time_limit": 60, "description": "平衡模式"},
    "thorough": {"time_limit": 120, "description": "深度求解"},
}


# ==================== 追踪常量 ====================

# GPS 更新间隔（秒）
DEFAULT_GPS_UPDATE_INTERVAL: float = 5.0

# 轨迹历史最大长度
MAX_TRAJECTORY_HISTORY: int = 1000

# 默认位置噪声（度）
DEFAULT_POSITION_NOISE: float = 0.0001


# ==================== API 常量 ====================

# 任务状态
JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"

# 任务超时（秒）
JOB_TIMEOUT_SECONDS: int = 600
