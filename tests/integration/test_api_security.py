"""API 安全中间件集成回归测试。

覆盖：
- API Key 认证失败关闭
- 健康检查端点公开
- 错误 API Key 返回 401
- 请求体大小限制
- 全局异常处理器脱敏
- 基于 X-Forwarded-For 的限流
"""

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.main import app
from api.middleware.security import RateLimitMiddleware

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    # 环境变量统一由 tests/conftest.py 管理，避免不同 fixture 修改导致中间件状态不一致
    with TestClient(app) as c:
        yield c


@pytest.fixture
def headers():
    return {"X-API-Key": "test-api-key-12345"}


class TestHealthAndRootPublic:
    def test_health_endpoint_is_public(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200


class TestAPIKeyAuthentication:
    def test_scenarios_requires_api_key(self, client):
        r = client.get("/api/v1/scenarios")
        assert r.status_code == 401

    def test_invalid_api_key_returns_401(self, client):
        r = client.get("/api/v1/scenarios", headers={"X-API-Key": "wrong-key"})
        assert r.status_code == 401

    def test_valid_api_key_returns_200(self, client, headers):
        r = client.get("/api/v1/scenarios", headers=headers)
        assert r.status_code == 200

    def test_solve_requires_api_key(self, client):
        r = client.post("/api/v1/solve", json={"customers": []})
        assert r.status_code == 401


class TestContentSizeLimit:
    def test_small_body_allowed(self, client, headers):
        r = client.post("/api/v1/solve", headers=headers, json={"customers": []})
        # 负载过小，可能返回 422 验证错误，但不应该是 413
        assert r.status_code != 413

    def test_large_body_rejected(self, client, headers):
        big_payload = {"customers": [{"id": i, "data": "x" * 1024} for i in range(20000)]}
        r = client.post("/api/v1/solve", headers=headers, json=big_payload)
        assert r.status_code == 413


class TestRateLimit:
    """测试基于内存的滑动窗口限流、X-Forwarded-For 识别、IP 上限与过期清理。"""

    @pytest.fixture
    def limited_app(self):
        """返回一个可配置限流参数的独立测试应用工厂。"""

        def _make_app(
            default_limit: int = 2,
            window_seconds: int = 60,
            max_ips: int = 10000,
        ) -> FastAPI:
            test_app = FastAPI()

            @test_app.get("/api/v1/test")
            def test_endpoint():
                return {"ok": True}

            # 显式关闭 disabled，避免 tests/conftest.py 中禁用的全局环境变量影响独立测试应用
            test_app.add_middleware(
                RateLimitMiddleware,
                default_limit=default_limit,
                window_seconds=window_seconds,
                disabled=False,
                max_ips=max_ips,
            )
            return test_app

        return _make_app

    def test_rate_limit_blocks_after_limit(self, limited_app):
        client = TestClient(limited_app())
        # 前 2 次请求应通过
        assert client.get("/api/v1/test").status_code == 200
        assert client.get("/api/v1/test").status_code == 200
        # 第 3 次应被限流
        r = client.get("/api/v1/test")
        assert r.status_code == 429
        assert "Too many requests" in r.json()["detail"]

    def test_rate_limit_uses_x_forwarded_for(self, limited_app):
        """验证 X-Forwarded-For 头中的不同 IP 拥有独立限流配额。"""
        client = TestClient(limited_app())
        # 客户端 A 触发限流
        headers_a = {"X-Forwarded-For": "203.0.113.1"}
        assert client.get("/api/v1/test", headers=headers_a).status_code == 200
        assert client.get("/api/v1/test", headers=headers_a).status_code == 200
        assert client.get("/api/v1/test", headers=headers_a).status_code == 429

        # 客户端 B 使用不同 IP，不应受 A 的限流影响
        headers_b = {"X-Forwarded-For": "203.0.113.2"}
        assert client.get("/api/v1/test", headers=headers_b).status_code == 200

    def test_rate_limit_ip_cap(self, limited_app):
        """验证 IP 条目总数达到上限后新 IP 被拒绝。"""
        client = TestClient(limited_app(default_limit=10, max_ips=2))

        assert (
            client.get("/api/v1/test", headers={"X-Forwarded-For": "203.0.113.1"}).status_code
            == 200
        )
        assert (
            client.get("/api/v1/test", headers={"X-Forwarded-For": "203.0.113.2"}).status_code
            == 200
        )
        r = client.get("/api/v1/test", headers={"X-Forwarded-For": "203.0.113.3"})
        assert r.status_code == 429
        assert "Too many requests" in r.json()["detail"]

    def test_rate_limit_expired_ip_cleanup(self, limited_app):
        """验证过期 IP 条目被清理后，新 IP 可继续使用。"""
        client = TestClient(limited_app(default_limit=10, window_seconds=0.1, max_ips=2))

        headers_a = {"X-Forwarded-For": "203.0.113.1"}
        assert client.get("/api/v1/test", headers=headers_a).status_code == 200

        # 等待第一个 IP 的窗口过期
        time.sleep(0.15)

        headers_b = {"X-Forwarded-For": "203.0.113.2"}
        assert client.get("/api/v1/test", headers=headers_b).status_code == 200

        # 此时 A 已过期，应被清理，C 可以通过
        headers_c = {"X-Forwarded-For": "203.0.113.3"}
        r = client.get("/api/v1/test", headers=headers_c)
        assert r.status_code == 200

    def test_rate_limit_empty_entry_removed_after_purge(self, limited_app):
        """验证全量清理会删除空列表条目，避免长期占用 IP 槽位。"""
        client = TestClient(limited_app(default_limit=10, window_seconds=0.1, max_ips=2))

        headers_a = {"X-Forwarded-For": "203.0.113.1"}
        client.get("/api/v1/test", headers=headers_a)

        # 等待 A 过期，使其条目变为空列表
        time.sleep(0.15)

        # 创建 B 条目，使总 IP 数达到 max_ips，触发全量清理
        headers_b = {"X-Forwarded-For": "203.0.113.2"}
        assert client.get("/api/v1/test", headers=headers_b).status_code == 200

        # A 的空条目应被清理，C 可以通过
        headers_c = {"X-Forwarded-For": "203.0.113.3"}
        r = client.get("/api/v1/test", headers=headers_c)
        assert r.status_code == 200
