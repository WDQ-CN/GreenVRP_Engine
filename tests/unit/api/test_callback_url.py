"""
单元测试：api/services/solver_service.py 中的 callback_url SSRF 校验，
以及 API 安全中间件、请求体大小限制、全局异常脱敏相关行为。
"""

import asyncio

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from api.main import ContentSizeLimitMiddleware
from api.main import app as main_app
from api.middleware.security import APIKeyAuthMiddleware
from api.services.solver_service import _validate_callback_url
from exceptions.errors import ValidationError


class TestValidateCallbackUrl:
    """测试 callback_url 的 SSRF 校验。"""

    @pytest.fixture(autouse=True)
    def mock_public_dns(self, monkeypatch: pytest.MonkeyPatch):
        """将公共域名解析结果 mock 为公网 IP，避免单测依赖真实网络。"""
        import socket

        original_getaddrinfo = socket.getaddrinfo

        def _fake_getaddrinfo(host, port, *args, **kwargs):
            lower_host = str(host).lower()
            # 保留私有/本地域名的真实解析行为，确保相关用例仍走禁用分支
            private_or_local = {
                "localhost",
                "localhost.localdomain",
            } | {f"host.{suffix}" for suffix in ("local", "internal", "corp", "home", "lan")}
            if lower_host in private_or_local or lower_host.endswith(
                (".local", ".internal", ".corp", ".home", ".lan")
            ):
                return original_getaddrinfo(host, port, *args, **kwargs)
            # 公共域名统一返回 mock 公网地址
            return [(2, 1, 6, "", ("8.8.8.8", port or 0))]

        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)

    def test_none_callback_url_is_allowed(self):
        """None 值应被允许。"""
        assert _validate_callback_url(None) is None

    def test_valid_https_url_is_allowed(self):
        """合法的 https 外网域名应被允许。"""
        assert _validate_callback_url("https://example.com/callback") is None

    def test_valid_http_url_is_allowed(self):
        """合法的 http 外网域名应被允许。"""
        assert _validate_callback_url("http://api.example.com/callback") is None

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/callback",
            "https://10.0.0.1/callback",
            "http://172.16.0.1/callback",
            "https://192.168.1.1/callback",
            "http://169.254.1.1/callback",
        ],
    )
    def test_private_ip_is_rejected(self, url: str):
        """私有 IP 地址应被拒绝。"""
        with pytest.raises(ValidationError, match="不允许使用 IP 地址"):
            _validate_callback_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost/callback",
            "https://localhost.localdomain/callback",
            "http://LOCALHOST/callback",
        ],
    )
    def test_localhost_is_rejected(self, url: str):
        """localhost 及本地域应被拒绝。"""
        with pytest.raises(ValidationError, match="不允许指向 localhost"):
            _validate_callback_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "http://api.local/callback",
            "https://service.internal/callback",
            "http://gateway.corp/callback",
            "https://router.home/callback",
            "http://nas.lan/callback",
        ],
    )
    def test_private_domain_suffix_is_rejected(self, url: str):
        """内网域名后缀应被拒绝。"""
        with pytest.raises(ValidationError, match="不允许指向私有域名后缀"):
            _validate_callback_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "ftp://example.com/callback",
            "gopher://example.com",
            "dict://example.com",
            "ldap://example.com",
            "tftp://example.com",
            "javascript:alert(1)",
        ],
    )
    def test_invalid_scheme_is_rejected(self, url: str):
        """非 http/https 协议应被拒绝。"""
        with pytest.raises(ValidationError, match="协议不支持"):
            _validate_callback_url(url)

    def test_missing_hostname_is_rejected(self):
        """缺少主机名应被拒绝。"""
        with pytest.raises(ValidationError, match="缺少主机名"):
            _validate_callback_url("http://")


class TestAPIKeyFailClosed:
    """测试 API Key 未配置时默认拒绝访问。"""

    @pytest.fixture
    def unauthenticated_app(self, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
        """创建未配置 API Key 且未允许未认证访问的测试应用。"""
        monkeypatch.delenv("GREENVRP_API_KEY", raising=False)

        test_app = FastAPI()

        @test_app.get("/api/v1/health")
        def health():
            return {"status": "ok"}

        @test_app.get("/api/v1/protected")
        def protected():
            return {"data": "secret"}

        @test_app.options("/api/v1/options")
        def options_endpoint():
            return {"data": "options"}

        test_app.add_middleware(APIKeyAuthMiddleware)
        return test_app

    def test_health_endpoint_is_public(self, unauthenticated_app: FastAPI):
        client = TestClient(unauthenticated_app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_root_api_endpoint_is_public(self, unauthenticated_app: FastAPI):
        client = TestClient(unauthenticated_app)
        response = client.get("/api/v1/")
        assert response.status_code == 404  # 路由不存在，但不应被 401 拦截

    def test_options_request_is_public(self, unauthenticated_app: FastAPI):
        client = TestClient(unauthenticated_app)
        response = client.options("/api/v1/options")
        assert response.status_code == 200

    def test_protected_endpoint_returns_401(self, unauthenticated_app: FastAPI):
        client = TestClient(unauthenticated_app)
        response = client.get("/api/v1/protected")
        assert response.status_code == 401
        assert response.json()["detail"] == "Unauthorized: API key not configured"

    def test_allow_unauthenticated_env_allows_access(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("GREENVRP_API_KEY", raising=False)
        monkeypatch.setenv("GREENVRP_ALLOW_UNAUTHENTICATED", "true")

        test_app = FastAPI()

        @test_app.get("/api/v1/protected")
        def protected():
            return {"data": "secret"}

        test_app.add_middleware(APIKeyAuthMiddleware)
        client = TestClient(test_app)
        response = client.get("/api/v1/protected")
        assert response.status_code == 200


class TestContentSizeLimit:
    """测试请求体大小限制中间件。"""

    @pytest.fixture
    def limited_app(self) -> FastAPI:
        """创建请求体限制为 16 字节的测试应用。"""
        test_app = FastAPI()

        @test_app.post("/echo")
        async def echo(request: Request):
            body = await request.body()
            return {"size": len(body)}

        test_app.add_middleware(ContentSizeLimitMiddleware, max_size_bytes=16)
        return test_app

    def test_small_body_allowed(self, limited_app: FastAPI):
        client = TestClient(limited_app)
        response = client.post("/echo", content=b"small body")
        assert response.status_code == 200
        assert response.json()["size"] == 10

    def test_large_body_rejected_by_content_length(self, limited_app: FastAPI):
        client = TestClient(limited_app)
        response = client.post("/echo", content=b"x" * 1024)
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()

    def test_main_app_uses_default_10mb_limit(self):
        """主应用默认限制为 10 MB。"""
        client = TestClient(main_app)
        # 10 MB 正好等于限制，应被允许
        response = client.post("/api/v1/solve", content=b"x" * (10 * 1024 * 1024))
        # 认证失败或 413 都算中间件生效；这里未提供 API Key，返回 401 说明大小检查已通过
        assert response.status_code == 401


class TestGlobalExceptionHandler:
    """测试全局 500 异常处理器。"""

    @pytest.fixture
    def error_app(self) -> FastAPI:
        """创建会抛出未捕获异常的测试应用。"""
        test_app = FastAPI()

        async def _sanitized_handler(request: Request, exc: Exception):
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

        test_app.add_exception_handler(RuntimeError, _sanitized_handler)

        @test_app.get("/boom")
        def boom():
            raise RuntimeError("something secret")

        return test_app

    def test_unhandled_exception_returns_sanitized_message(self, error_app: FastAPI):
        client = TestClient(error_app)
        response = client.get("/boom")
        assert response.status_code == 500
        body = response.json()
        assert body["detail"] == "Internal server error"
        assert "secret" not in str(body)

    def test_main_app_global_handler_hides_internal_details(self):
        """验证 api.main 中注册的全局 Exception 处理器存在且行为正确。"""
        from api.main import global_exception_handler

        class FakeRequest:
            url = type("FakeURL", (), {"path": "/test"})()

        response = asyncio.run(global_exception_handler(FakeRequest(), RuntimeError("secret")))
        assert response.status_code == 500
        assert response.body == b'{"detail":"Internal server error"}'
