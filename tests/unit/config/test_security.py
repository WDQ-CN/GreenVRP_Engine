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
