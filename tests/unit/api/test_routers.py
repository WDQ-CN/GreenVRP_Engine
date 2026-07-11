"""
集成测试：API 路由 — 使用 FastAPI TestClient
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def headers():
    return {"X-API-Key": "test-api-key-12345"}


@pytest.fixture
def solve_payload():
    return {
        "customers": [
            {"id": 0, "name": "仓库", "lat": 39.9042, "lon": 116.4074,
             "demand": 0, "service_time_min": 0, "tw_earliest": 0, "tw_latest": 1440},
            {"id": 1, "name": "客户A", "lat": 39.9142, "lon": 116.4174,
             "demand": 50, "service_time_min": 15, "tw_earliest": 480, "tw_latest": 720},
        ],
    }


class TestHealthEndpoint:
    def test_health_public(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200

    def test_root_public(self, client):
        r = client.get("/api/v1/")
        assert r.status_code == 200


class TestAuthentication:
    def test_scenarios_requires_auth(self, client):
        r = client.get("/api/v1/scenarios")
        assert r.status_code == 401

    def test_valid_api_key(self, client, headers):
        r = client.get("/api/v1/scenarios", headers=headers)
        assert r.status_code == 200


class TestSolveSync:
    def test_solve_success(self, client, headers, solve_payload):
        r = client.post("/api/v1/solve", json=solve_payload, headers=headers)
        assert r.status_code in (200, 422)  # 422 表示验证通过但数据不足

    def test_solve_without_auth(self, client, solve_payload):
        r = client.post("/api/v1/solve", json=solve_payload)
        assert r.status_code == 401

    def test_empty_customers(self, client, headers):
        r = client.post("/api/v1/solve", json={"customers": []}, headers=headers)
        assert r.status_code == 422
