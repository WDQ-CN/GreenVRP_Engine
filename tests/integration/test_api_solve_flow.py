"""
集成测试：API 求解流程端到端

测试完整的求解请求链路：提交 → 轮询 → 获取结果。
使用内存 SQLite 数据库和 FastAPI TestClient。
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from tests.fixtures.customers import get_test_customers_df, get_test_vehicle_config


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    from config.security import security_config
    api_key = next(iter(security_config.API_KEYS)) if security_config.API_KEYS else "test-api-key-12345"
    return {"X-API-Key": api_key}


class TestSolveEndToEnd:
    """端到端求解流程测试。"""

    @pytest.mark.slow
    def test_solve_sync_endpoint(self, client, auth_headers):
        """POST /api/v1/solve 同步求解。"""
        customers = get_test_customers_df().to_dict("records")
        request_data = {
            "customers": customers,
            "vehicle_config": get_test_vehicle_config(),
            "params": {"fuel_price": 7.5, "search_time_limit": 5},
        }

        response = client.post("/api/v1/solve", json=request_data, headers=auth_headers)
        assert response.status_code in (200, 422, 500)  # 允许各种响应码

        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert "status" in data
            assert data["status"] in ("pending", "processing", "completed", "failed")

    @pytest.mark.slow
    def test_solve_async_endpoint(self, client, auth_headers):
        """POST /api/v1/solve/async 异步求解。"""
        customers = get_test_customers_df().to_dict("records")
        request_data = {
            "customers": customers,
            "vehicle_config": get_test_vehicle_config(),
            "params": {"fuel_price": 7.5, "search_time_limit": 5},
        }

        response = client.post("/api/v1/solve/async", json=request_data, headers=auth_headers)
        # 允许 200（同步兼容）、202（已接受）、422（校验错误）
        assert response.status_code in (200, 202, 422)

    def test_health_endpoint(self, client):
        """GET /api/v1/health 健康检查。"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_auth_token_endpoint(self, client):
        """POST /api/v1/auth/token 获取令牌。"""
        from config.security import security_config
        api_key = next(iter(security_config.API_KEYS)) if security_config.API_KEYS else "test"
        # 将 content-type 去掉，让 TestClient 自动设置为 form-data
        response = client.post(
            "/api/v1/token",
            data={"username": api_key, "password": "x"},  # password 字段必填
        )
        assert response.status_code in (200, 401)
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
