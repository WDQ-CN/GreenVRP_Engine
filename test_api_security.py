"""
验证修复后的 API 安全中间件：
1. API Key 认证
2. 基于 IP 的限流
3. 求解接口基本可用性
"""

import os
import time

import httpx

os.environ.setdefault("GREENVRP_API_KEY", "test-api-key-12345")
os.environ.setdefault("GREENVRP_ALLOWED_ORIGINS", "http://localhost:3000")

BASE_URL = "http://127.0.0.1:8000/api/v1"
HEADERS = {"X-API-Key": "test-api-key-12345"}
INVALID_HEADERS = {"X-API-Key": "wrong-key"}


def check(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"[FAIL] {name}: {detail}")


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    r = client.get("/health")
    check("GET /health 无需认证返回 200", r.status_code == 200, f"status={r.status_code}")

    r = client.get("/scenarios")
    check("无 API Key 访问 /scenarios 返回 401", r.status_code == 401, f"status={r.status_code}")

    r = client.get("/scenarios", headers=INVALID_HEADERS)
    check("错误 API Key 返回 401", r.status_code == 401, f"status={r.status_code}")

    r = client.get("/scenarios", headers=HEADERS)
    check("正确 API Key 访问 /scenarios 返回 200", r.status_code == 200, f"status={r.status_code}")

    r = client.post("/solve", json={"customers": []})
    check("无 API Key POST /solve 返回 401", r.status_code == 401, f"status={r.status_code}")

    valid_payload = {
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
        "params": {"search_time_limit": 5},
    }

    r = client.post("/solve", json=valid_payload, headers=HEADERS)
    check(
        "正确 API Key + 有效负载 POST /solve 返回 200",
        r.status_code == 200,
        f"status={r.status_code}",
    )
    if r.status_code == 200:
        body = r.json()
        check("返回包含 solution", "solution" in body)
        check("返回包含 cost_result", "cost_result" in body)

    rate_limit_hit = False
    for _i in range(12):
        r = client.post("/solve", json=valid_payload, headers=HEADERS)
        if r.status_code == 429:
            rate_limit_hit = True
            break
        if r.status_code not in (200, 422):
            break
        time.sleep(0.1)
    check("限流在 12 次请求内触发", rate_limit_hit)


if __name__ == "__main__":
    main()
