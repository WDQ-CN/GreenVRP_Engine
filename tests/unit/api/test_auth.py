"""
单元测试：api/security/auth.py — 认证模块安全策略
"""

import pytest
from datetime import timedelta


class TestCreateAccessTokenSecurity:
    """create_access_token 安全策略测试。"""

    def test_production_default_key_raises(self, monkeypatch):
        """生产环境使用默认密钥创建 token 必须抛出 ValueError。"""
        from config.security import security_config
        from api.security.auth import create_access_token

        monkeypatch.setattr(security_config, "ENV", "production")
        monkeypatch.setattr(
            security_config, "JWT_SECRET_KEY",
            "change-this-secret-key-in-production-min-32-chars"
        )

        with pytest.raises(ValueError, match="生产环境禁止使用默认 JWT 密钥"):
            create_access_token({"sub": "test"})

    def test_development_default_key_allowed(self, monkeypatch):
        """开发环境使用默认密钥创建 token 只警告不抛出异常。"""
        from config.security import security_config
        from api.security.auth import create_access_token

        monkeypatch.setattr(security_config, "ENV", "development")
        monkeypatch.setattr(
            security_config, "JWT_SECRET_KEY",
            "change-this-secret-key-in-production-min-32-chars"
        )

        # 不应抛出异常
        token = create_access_token({"sub": "test"})
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_production_custom_key_works(self, monkeypatch):
        """生产环境使用自定义密钥创建 token 应正常工作。"""
        from config.security import security_config
        from api.security.auth import create_access_token

        monkeypatch.setattr(security_config, "ENV", "production")
        monkeypatch.setattr(
            security_config, "JWT_SECRET_KEY",
            "my-custom-production-secret-key-32-chars!"
        )

        token = create_access_token({"sub": "test"})
        assert token is not None
        assert isinstance(token, str)

    def test_token_with_expires_delta(self, monkeypatch):
        """带过期时间的 token 创建。"""
        from config.security import security_config
        from api.security.auth import create_access_token

        monkeypatch.setattr(security_config, "ENV", "development")
        monkeypatch.setattr(
            security_config, "JWT_SECRET_KEY",
            "test-secret-key-for-testing-min-32-chars!!"
        )

        token = create_access_token(
            {"sub": "test"},
            expires_delta=timedelta(minutes=30)
        )
        assert token is not None
        assert isinstance(token, str)

    def test_token_contains_expected_parts(self, monkeypatch):
        """JWT token 结构应为三段式。"""
        from config.security import security_config
        from api.security.auth import create_access_token

        monkeypatch.setattr(security_config, "ENV", "development")
        monkeypatch.setattr(
            security_config, "JWT_SECRET_KEY",
            "test-secret-key-for-testing-min-32-chars!!"
        )

        token = create_access_token({"sub": "test_user"})
        parts = token.split(".")
        assert len(parts) == 3  # header.payload.signature

    def test_your_secret_prefix_also_blocked_in_production(self, monkeypatch):
        """'your-secret' 前缀的密钥在生产环境也应被阻断。"""
        from config.security import security_config
        from api.security.auth import create_access_token

        monkeypatch.setattr(security_config, "ENV", "production")
        monkeypatch.setattr(
            security_config, "JWT_SECRET_KEY",
            "your-secret-key-that-is-still-weak"
        )

        with pytest.raises(ValueError, match="生产环境禁止使用默认 JWT 密钥"):
            create_access_token({"sub": "test"})


class TestVerifyTokenSecurity:
    """verify_token 安全策略测试。"""

    def test_expired_token_raises(self, monkeypatch):
        """过期 token 应抛出 HTTPException(401)。"""
        from datetime import datetime, timezone, timedelta
        from jose import jwt
        from fastapi import HTTPException
        from config.security import security_config
        from api.security.auth import verify_token

        monkeypatch.setattr(security_config, "ENV", "development")
        monkeypatch.setattr(
            security_config, "JWT_SECRET_KEY",
            "test-secret-key-for-testing-min-32-chars!!"
        )

        # 创建一个已过期的 token
        expired_payload = {
            "sub": "test",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(
            expired_payload,
            security_config.JWT_SECRET_KEY,
            algorithm=security_config.JWT_ALGORITHM,
        )

        with pytest.raises(HTTPException) as excinfo:
            verify_token(token=expired_token)
        assert excinfo.value.status_code == 401

    def test_invalid_signature_raises(self, monkeypatch):
        """无效签名的 token 应抛出 HTTPException(401)。"""
        from fastapi import HTTPException
        from api.security.auth import verify_token

        # 使用不同密钥签名的 token
        invalid_token = (
            "eyJhbGciOiJIUzI1NiJ9"
            ".eyJzdWIiOiJ0ZXN0In0"
            ".invalidsignature123"
        )

        with pytest.raises(HTTPException) as excinfo:
            verify_token(token=invalid_token)
        assert excinfo.value.status_code == 401

    def test_none_token_returns_none(self):
        """None token 应返回 None 而不是抛出异常。"""
        from api.security.auth import verify_token

        result = verify_token(token=None)
        assert result is None
