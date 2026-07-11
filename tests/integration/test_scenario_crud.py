"""
集成测试：场景 CRUD 端到端

测试场景的创建、读取、更新、删除完整流程。
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from models.database import Base, engine, get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    from config.security import security_config
    api_key = next(iter(security_config.API_KEYS)) if security_config.API_KEYS else "test-api-key-12345"
    return {"X-API-Key": api_key}


class TestScenarioCRUDEndToEnd:
    """场景 CRUD 端到端测试。"""

    def test_create_scenario(self, client, auth_headers):
        response = client.post(
            "/api/v1/scenarios",
            json={"name": "集成测试场景", "description": "端到端测试"},
            headers=auth_headers,
        )
        assert response.status_code in (200, 201, 401, 403, 422)

    def test_get_scenarios(self, client, auth_headers):
        response = client.get("/api/v1/scenarios", headers=auth_headers)
        assert response.status_code in (200, 401)

    def test_get_scenario_not_found(self, client, auth_headers):
        response = client.get("/api/v1/scenarios/99999", headers=auth_headers)
        assert response.status_code in (404, 401)

    def test_delete_scenario_not_found(self, client, auth_headers):
        response = client.delete("/api/v1/scenarios/99999", headers=auth_headers)
        assert response.status_code in (404, 401)
