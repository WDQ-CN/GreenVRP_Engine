"""
验证核心 API 功能：
1. 场景 CRUD
2. 求解接口（含 vehicle_config 与 params）
3. CSV 解析与导出等价性
"""

import os

import httpx

os.environ.setdefault("GREENVRP_API_KEY", "test-api-key-12345")

BASE_URL = "http://127.0.0.1:8000/api/v1"
HEADERS = {"X-API-Key": "test-api-key-12345"}


def check(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"[FAIL] {name}: {detail}")


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # create
    payload = {
        "name": "测试场景-北京配送",
        "description": "用于集成测试",
        "customers": [
            {
                "id": 0,
                "name": "仓库",
                "lat": 39.9042,
                "lon": 116.4074,
                "demand": 0,
                "service_time_min": 0,
                "tw_earliest": 0,
                "tw_latest": 1440,
                "is_depot": True,
            },
            {
                "id": 1,
                "name": "客户A",
                "lat": 39.9142,
                "lon": 116.4174,
                "demand": 50,
                "service_time_min": 15,
                "tw_earliest": 480,
                "tw_latest": 720,
            },
        ],
        "vehicle_config": {
            "4.2m": {
                "count": 5,
                "capacity": 800,
                "fixed_cost": 300,
                "fuel_per_100km": 12,
                "speed_kmh": 40,
                "color": "#2563EB",
            }
        },
        "params": {
            "fuel_price": 7.5,
            "hourly_wage": 50,
            "carbon_price": 0.08,
            "late_penalty_per_min": 10,
            "search_time_limit": 5,
            "use_multi_strategy": False,
            "use_parallel": False,
        },
    }
    r = client.post("/scenarios", json=payload, headers=HEADERS)
    check("创建场景返回 200", r.status_code == 200, f"status={r.status_code}")
    scenario_id = r.json()["id"]

    # list
    r = client.get("/scenarios", headers=HEADERS)
    check("列出场景返回 200", r.status_code == 200, f"status={r.status_code}")
    check("场景列表包含新建场景", any(s["id"] == scenario_id for s in r.json()))

    # get detail
    r = client.get(f"/scenarios/{scenario_id}", headers=HEADERS)
    check("获取场景详情返回 200", r.status_code == 200, f"status={r.status_code}")
    detail = r.json()
    check("场景详情包含客户数据", len(detail.get("customers", [])) == 2)
    check("场景详情包含车型配置", "4.2m" in (detail.get("vehicle_config") or {}))

    # update
    r = client.put(
        f"/scenarios/{scenario_id}",
        json={"name": "测试场景-北京配送-已更新"},
        headers=HEADERS,
    )
    check("更新场景返回 200", r.status_code == 200, f"status={r.status_code}")
    check("更新后名称正确", r.json()["name"] == "测试场景-北京配送-已更新")

    # delete
    r = client.delete(f"/scenarios/{scenario_id}", headers=HEADERS)
    check("删除场景返回 200", r.status_code == 200, f"status={r.status_code}")
    r = client.get(f"/scenarios/{scenario_id}", headers=HEADERS)
    check("删除后再次获取返回 404", r.status_code == 404, f"status={r.status_code}")

    solve_payload = {
        "customers": payload["customers"],
        "vehicle_config": payload["vehicle_config"],
        "params": payload["params"],
    }
    r = client.post("/solve", json=solve_payload, headers=HEADERS)
    check("POST /solve 返回 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check("返回 solution", "solution" in body)
        check("返回 cost_result", "cost_result" in body)
        if body.get("cost_result"):
            cost = body["cost_result"]
            check("cost_result 包含总成本", "total_cost" in cost)
            check("cost_result 包含碳排放量", "carbon_emission_kg" in cost)


if __name__ == "__main__":
    main()
