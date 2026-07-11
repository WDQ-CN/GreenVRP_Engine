"""
测试夹具：提供共享的测试数据。
"""

import pandas as pd


def get_test_customers_df() -> pd.DataFrame:
    """返回用于测试的小型客户数据集（含仓库）。"""
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


def get_test_vehicle_config() -> dict:
    """返回用于测试的车型配置。"""
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


def get_test_params() -> dict:
    """返回用于测试的全局参数。"""
    return {
        "fuel_price": 7.5,
        "hourly_wage": 50.0,
        "carbon_price": 0.08,
        "late_penalty_per_min": 10.0,
    }


def get_invalid_customers_df() -> pd.DataFrame:
    """返回包含无效时间窗的客户数据，用于验证测试。"""
    data = {
        "id": [0, 1],
        "name": ["仓库", "客户A"],
        "lat": [39.9042, 39.9123],
        "lon": [116.4074, 116.3456],
        "demand": [0, 45],
        "service_time_min": [0, 15],
        "tw_earliest": [480, 700],
        "tw_latest": [960, 600],  # 无效： earliest > latest
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
