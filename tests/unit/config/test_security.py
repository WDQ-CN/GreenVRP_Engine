"""
单元测试：config/security.py — 安全配置与校验
"""

import pytest
from config.security import security_config


class TestValidateCallbackUrl:
    def test_empty_url_allowed(self):
        """空 URL（可选回调）应通过验证。"""
        valid, msg = security_config.validate_callback_url("")
        assert valid is True
        assert msg == ""

    def test_valid_https_url(self):
        """有效的 HTTPS URL 应通过。"""
        # 使用白名单中的 URL
        valid, msg = security_config.validate_callback_url(
            "https://example.com/callback")
        assert valid is True

    def test_http_rejected(self):
        """非 HTTPS 应拒绝。"""
        valid, msg = security_config.validate_callback_url(
            "http://example.com/callback")
        assert valid is False

    def test_localhost_rejected(self):
        """localhost 应拒绝。"""
        valid, msg = security_config.validate_callback_url(
            "https://localhost/callback")
        assert valid is False

    def test_private_ip_rejected(self):
        """内网 IP 应拒绝。"""
        valid, msg = security_config.validate_callback_url(
            "https://192.168.1.1/callback")
        assert valid is False

    def test_ip_127_rejected(self):
        """127.0.0.1 应拒绝。"""
        valid, msg = security_config.validate_callback_url(
            "https://127.0.0.1/callback")
        assert valid is False

    def test_invalid_url_format(self):
        """无效 URL 格式应拒绝。"""
        valid, msg = security_config.validate_callback_url("not-a-url")
        assert valid is False


class TestValidateApiKey:
    def test_empty_key(self):
        """空 Key 应拒绝。"""
        valid, msg = security_config.validate_api_key_format("")
        assert valid is False

    def test_short_key(self):
        """少于 16 字符应拒绝。"""
        valid, msg = security_config.validate_api_key_format("short")
        assert valid is False

    def test_valid_key(self):
        """符合要求的 Key 应通过。"""
        valid, msg = security_config.validate_api_key_format(
            "valid-api-key-12345")
        assert valid is True

    def test_special_chars_rejected(self):
        """特殊字符应拒绝。"""
        valid, msg = security_config.validate_api_key_format(
            "invalid-key!@#$")
        assert valid is False


class TestIsPrivateIp:
    def test_private_10(self):
        assert security_config._is_private_ip("10.0.0.1") is True

    def test_private_172(self):
        assert security_config._is_private_ip("172.16.0.1") is True

    def test_private_192(self):
        assert security_config._is_private_ip("192.168.1.1") is True

    def test_loopback(self):
        assert security_config._is_private_ip("127.0.0.1") is True

    def test_link_local(self):
        assert security_config._is_private_ip("169.254.1.1") is True

    def test_public_ip(self):
        assert security_config._is_private_ip("8.8.8.8") is False

    def test_invalid_ip(self):
        """无效 IP 应视为不安全。"""
        assert security_config._is_private_ip("not-an-ip") is True


class TestJwtSecretKey:
    """JWT 密钥安全策略测试（生产环境默认密钥必须阻断）。"""

    def test_default_key_in_production_raises(self, monkeypatch):
        """生产环境使用默认 JWT 密钥必须抛出 RuntimeError。"""
        import importlib
        import config.security

        # 模拟生产环境并删除密钥环境变量
        monkeypatch.setenv("GREENVRP_ENV", "production")
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        with pytest.raises(RuntimeError, match="必须设置 JWT_SECRET_KEY"):
            importlib.reload(config.security)

    def test_development_default_key_allowed(self, monkeypatch):
        """开发环境使用默认 JWT 密钥只警告不抛出异常。"""
        import importlib
        import config.security

        monkeypatch.setenv("GREENVRP_ENV", "development")
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        # 不应抛出异常
        importlib.reload(config.security)
        # 验证密钥为默认值
        assert config.security.security_config.JWT_SECRET_KEY == \
            "change-this-secret-key-in-production-min-32-chars"

    def test_custom_key_in_production_works(self, monkeypatch):
        """生产环境使用自定义 JWT 密钥应正常工作。"""
        import importlib
        import config.security

        monkeypatch.setenv("GREENVRP_ENV", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "my-custom-production-secret-key-32-chars!")

        # 不应抛出异常
        importlib.reload(config.security)
        assert config.security.security_config.JWT_SECRET_KEY == \
            "my-custom-production-secret-key-32-chars!"
