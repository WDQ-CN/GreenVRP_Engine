"""核心 API 功能集成回归测试。

覆盖场景 CRUD、求解接口、callback_url SSRF 校验。
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    # 环境变量统一由 tests/conftest.py 管理，避免不同 fixture 修改导致中间件状态不一致
    with TestClient(app) as c:
        yield c


@pytest.fixture
def headers():
    return {"X-API-Key": "test-api-key-12345"}


@pytest.fixture
def scenario_payload():
    return {
        "name": "集成测试-北京配送",
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


class TestScenarioCRUD:
    def test_create_list_get_update_delete(self, client, headers, scenario_payload):
        # create
        r = client.post("/api/v1/scenarios", json=scenario_payload, headers=headers)
        assert r.status_code == 200
        scenario_id = r.json()["id"]

        # list（仅验证接口可用；若本地 DB 历史数据过多，新场景可能不在首页）
        r = client.get("/api/v1/scenarios", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

        # get detail
        r = client.get(f"/api/v1/scenarios/{scenario_id}", headers=headers)
        assert r.status_code == 200
        detail = r.json()
        assert len(detail.get("customers", [])) == 2
        assert "4.2m" in (detail.get("vehicle_config") or {})

        # update
        r = client.put(
            f"/api/v1/scenarios/{scenario_id}",
            json={"name": "集成测试-已更新"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "集成测试-已更新"

        # delete
        r = client.delete(f"/api/v1/scenarios/{scenario_id}", headers=headers)
        assert r.status_code == 200
        r = client.get(f"/api/v1/scenarios/{scenario_id}", headers=headers)
        assert r.status_code == 404


class TestSolveEndpoint:
    def test_solve_sync_success(self, client, headers, scenario_payload):
        solve_payload = {
            "customers": scenario_payload["customers"],
            "vehicle_config": scenario_payload["vehicle_config"],
            "params": scenario_payload["params"],
        }
        r = client.post("/api/v1/solve", json=solve_payload, headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert "solution" in body
        assert "cost_result" in body
        cost = body["cost_result"]
        assert "total_cost" in cost
        assert "carbon_emission_kg" in cost


class TestCallbackUrlValidation:
    def test_private_callback_url_rejected(self, client, headers, scenario_payload):
        solve_payload = {
            "customers": scenario_payload["customers"],
            "callback_url": "http://127.0.0.1/callback",
            "params": {"search_time_limit": 5},
        }
        r = client.post("/api/v1/solve/async", json=solve_payload, headers=headers)
        assert r.status_code == 422
        assert "不允许使用 IP 地址" in r.text or "callback_url" in r.text
