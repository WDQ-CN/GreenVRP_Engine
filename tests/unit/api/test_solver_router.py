"""
单元测试：api/routers/solver.py
使用 TestClient 进行路由测试。
"""

import os

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    api_key = os.getenv("GREENVRP_API_KEY", "test-api-key")
    return TestClient(app, headers={"X-API-Key": api_key})


class TestHealthCheck:
    def test_health_endpoint(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200


class TestSolveSync:
    def test_solve_sync_success(self, client):
        payload = {
            "customers": [
                {
                    "id": 0,
                    "name": "仓库",
                    "lat": 39.9042,
                    "lon": 116.4074,
                    "demand": 0,
                    "service_time_min": 0,
                    "tw_earliest": 480,
                    "tw_latest": 960,
                },
                {
                    "id": 1,
                    "name": "客户A",
                    "lat": 39.9123,
                    "lon": 116.3456,
                    "demand": 45,
                    "service_time_min": 15,
                    "tw_earliest": 500,
                    "tw_latest": 600,
                },
            ],
            "params": {
                "search_time_limit": 5,
                "use_multi_strategy": False,
            },
        }
        response = client.post("/api/v1/solve", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "solution" in data

    def test_solve_sync_invalid_customer(self, client):
        payload = {
            "customers": [
                {
                    "id": 0,
                    "name": "仓库",
                    "lat": 39.9,
                    "lon": 116.4,
                    "demand": 0,
                    "service_time_min": 0,
                    "tw_earliest": 700,
                    "tw_latest": 600,
                }
            ]
        }
        response = client.post("/api/v1/solve", json=payload)
        # Pydantic 会在请求层面拦截并返回 422
        assert response.status_code == 422


class TestSolveAsync:
    def test_solve_async_creates_job(self, client):
        payload = {
            "customers": [
                {
                    "id": 0,
                    "name": "仓库",
                    "lat": 39.9042,
                    "lon": 116.4074,
                    "demand": 0,
                    "service_time_min": 0,
                    "tw_earliest": 480,
                    "tw_latest": 960,
                },
                {
                    "id": 1,
                    "name": "客户A",
                    "lat": 39.9123,
                    "lon": 116.3456,
                    "demand": 45,
                    "service_time_min": 15,
                    "tw_earliest": 500,
                    "tw_latest": 600,
                },
            ],
            "params": {
                "search_time_limit": 5,
                "use_multi_strategy": False,
            },
        }
        response = client.post("/api/v1/solve/async", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"


class TestJobsRouter:
    def test_get_job_status_not_found(self, client):
        response = client.get("/api/v1/jobs/non-existent-job-id")
        assert response.status_code == 404

    def test_get_job_result_not_found(self, client):
        response = client.get("/api/v1/jobs/non-existent-job-id/result")
        assert response.status_code == 404

    def test_job_lifecycle(self, client):
        payload = {
            "customers": [
                {
                    "id": 0,
                    "name": "仓库",
                    "lat": 39.9042,
                    "lon": 116.4074,
                    "demand": 0,
                    "service_time_min": 0,
                    "tw_earliest": 480,
                    "tw_latest": 960,
                },
                {
                    "id": 1,
                    "name": "客户A",
                    "lat": 39.9123,
                    "lon": 116.3456,
                    "demand": 45,
                    "service_time_min": 15,
                    "tw_earliest": 500,
                    "tw_latest": 600,
                },
            ],
            "params": {
                "search_time_limit": 5,
                "use_multi_strategy": False,
            },
        }
        # 创建异步任务
        create_resp = client.post("/api/v1/solve/async", json=payload)
        assert create_resp.status_code == 200
        job_id = create_resp.json()["job_id"]

        # 查询状态（可能已经 completed，因为当前实现是同步模拟）
        status_resp = client.get(f"/api/v1/jobs/{job_id}")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["job_id"] == job_id
        assert status_data["status"] in ("pending", "processing", "completed", "failed")

        # 如果已完成，查询结果
        if status_data["status"] == "completed":
            result_resp = client.get(f"/api/v1/jobs/{job_id}/result")
            assert result_resp.status_code == 200
            result_data = result_resp.json()
            assert "solution" in result_data
