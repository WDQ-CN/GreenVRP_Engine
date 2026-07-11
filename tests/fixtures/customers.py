"""
测试夹具：提供共享的测试数据。

包含用于各类测试的标准化客户、车辆、方案数据。
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd


def get_test_customers_df() -> pd.DataFrame:
    """返回用于测试的小型客户数据集（含仓库，6 个点）。"""
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


def get_large_customers_df(n_customers: int = 50) -> pd.DataFrame:
    """返回较大规模的客户数据集用于性能/压力测试。"""
    import numpy as np

    np.random.seed(42)
    # 仓库在中心
    ids = list(range(n_customers + 1))
    names = ["仓库"] + [f"客户{i}" for i in range(1, n_customers + 1)]

    # 北京地区随机坐标
    lats = [39.9042] + list(39.85 + np.random.rand(n_customers) * 0.3)
    lons = [116.4074] + list(116.30 + np.random.rand(n_customers) * 0.3)

    demands = [0] + list(np.random.randint(10, 100, n_customers))
    service_times = [0] + list(np.random.randint(10, 30, n_customers))

    # 时间窗：早上 8 点到下午 6 点之间随机
    tw_earliest = [480] + list(np.random.randint(420, 600, n_customers))
    tw_latest = [960] + [e + np.random.randint(60, 240) for e in tw_earliest[1:]]

    return pd.DataFrame({
        "id": ids,
        "name": names,
        "lat": lats,
        "lon": lons,
        "demand": demands,
        "service_time_min": service_times,
        "tw_earliest": tw_earliest,
        "tw_latest": tw_latest,
    })


def get_test_vehicle_config() -> dict:
    """返回用于测试的车型配置（2 种车型）。"""
    return {
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
    }


def get_single_type_vehicle_config() -> dict:
    """只有一种车型的配置。"""
    return {
        "4.2m": {
            "capacity": 800,
            "fixed_cost": 200,
            "fuel_per_100km": 12,
            "speed_kmh": 40,
            "count": 2,
            "color": "#1f77b4",
        },
    }


def get_test_params() -> dict:
    """返回用于测试的默认求解参数。"""
    return {
        "fuel_price": 7.5,
        "hourly_wage": 50.0,
        "carbon_price": 0.08,
        "late_penalty_per_min": 10.0,
    }


def get_custom_params(overrides: Optional[Dict[str, Any]] = None) -> dict:
    """返回带自定义覆盖的参数。"""
    params = get_test_params()
    if overrides:
        params.update(overrides)
    return params


def get_invalid_customers_df() -> pd.DataFrame:
    """返回包含无效时间窗的客户数据（earliest > latest）。"""
    data = {
        "id": [0, 1],
        "name": ["仓库", "客户A"],
        "lat": [39.9042, 39.9123],
        "lon": [116.4074, 116.3456],
        "demand": [0, 45],
        "service_time_min": [0, 15],
        "tw_earliest": [480, 700],
        "tw_latest": [960, 600],  # 无效：earliest > latest
    }
    return pd.DataFrame(data)


def get_minimal_solution() -> dict:
    """返回一个最小化的求解结果字典，用于成本/分析模块测试。"""
    return {
        "routes": [
            {
                "vehicle_id": 0,
                "vehicle_type": "4.2m",
                "vehicle_color": "#1f77b4",
                "capacity": 800,
                "stops": [
                    {
                        "node": 0,
                        "customer_id": 0,
                        "customer_name": "仓库",
                        "lat": 39.9042,
                        "lon": 116.4074,
                        "demand": 0,
                        "arrival_time": 480,
                        "service_time": 0,
                        "tw_earliest": 480,
                        "tw_latest": 960,
                        "late_minutes": 0,
                        "is_late": False,
                    },
                    {
                        "node": 1,
                        "customer_id": 1,
                        "customer_name": "客户A",
                        "lat": 39.9123,
                        "lon": 116.3456,
                        "demand": 45,
                        "arrival_time": 520,
                        "service_time": 15,
                        "tw_earliest": 500,
                        "tw_latest": 600,
                        "late_minutes": 0,
                        "is_late": False,
                    },
                ],
                "distance_km": 10.0,
                "total_demand": 45,
                "total_time_min": 15,
                "late_minutes": 0,
            }
        ],
        "total_distance": 10.0,
        "vehicles_used": {"4.2m": 1, "7.6m": 0},
        "total_late_minutes": 0,
        "solution_status": "SUCCESS",
    }


def get_multi_route_solution() -> dict:
    """返回多路线的求解结果。"""
    solution = get_minimal_solution()
    solution["routes"].append(
        {
            "vehicle_id": 1,
            "vehicle_type": "7.6m",
            "vehicle_color": "#2ca02c",
            "capacity": 1500,
            "stops": [
                {
                    "node": 0,
                    "customer_id": 0,
                    "customer_name": "仓库",
                    "lat": 39.9042,
                    "lon": 116.4074,
                    "demand": 0,
                    "arrival_time": 490,
                    "service_time": 0,
                    "tw_earliest": 480,
                    "tw_latest": 960,
                    "late_minutes": 0,
                    "is_late": False,
                },
                {
                    "node": 2,
                    "customer_id": 2,
                    "customer_name": "客户B",
                    "lat": 39.9456,
                    "lon": 116.3789,
                    "demand": 67,
                    "arrival_time": 540,
                    "service_time": 20,
                    "tw_earliest": 520,
                    "tw_latest": 640,
                    "late_minutes": 0,
                    "is_late": False,
                },
            ],
            "distance_km": 15.0,
            "total_demand": 67,
            "total_time_min": 20,
            "late_minutes": 0,
        }
    )
    solution["total_distance"] = 25.0
    solution["vehicles_used"] = {"4.2m": 1, "7.6m": 1}
    return solution


def get_solution_with_late_customer() -> dict:
    """返回包含迟到客户的求解结果。"""
    solution = get_minimal_solution()
    # 修改客户A 为迟到
    solution["routes"][0]["stops"][1]["arrival_time"] = 650  # 超过 tw_latest=600
    solution["routes"][0]["stops"][1]["late_minutes"] = 50
    solution["routes"][0]["stops"][1]["is_late"] = True
    solution["routes"][0]["late_minutes"] = 50
    solution["total_late_minutes"] = 50
    return solution
