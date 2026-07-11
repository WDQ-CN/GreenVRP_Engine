"""
API 认证模块

提供基于 API Key 和 JWT 的认证机制。
支持多种认证方式、令牌刷新和审计日志。
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated
from functools import lru_cache

from fastapi import Depends, HTTPException, Security, status, Request
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt, ExpiredSignatureError
from pydantic import BaseModel, Field

from config.security import security_config

# 配置日志
logger = logging.getLogger(__name__)

# API Key 认证
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# OAuth2 JWT 认证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


class TokenData(BaseModel):
    """Token 数据模型。"""

    username: Optional[str] = None
    api_key: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)
    exp: Optional[datetime] = None


class AuditLog(BaseModel):
    """审计日志模型。"""

    timestamp: datetime
    action: str
    user_type: str
    identifier: str
    ip_address: Optional[str] = None
    success: bool
    reason: Optional[str] = None


def _log_audit(
    action: str,
    user_type: str,
    identifier: str,
    success: bool,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """记录审计日志。"""
    log_entry = AuditLog(
        timestamp=datetime.now(timezone.utc),
        action=action,
        user_type=user_type,
        identifier=identifier,
        ip_address=ip_address,
        success=success,
        reason=reason,
    )
    if success:
        logger.info(f"Audit: {log_entry.model_dump_json()}")
    else:
        logger.warning(f"Audit Failed: {log_entry.model_dump_json()}")


@lru_cache(maxsize=1000)
def _cached_api_key_check(api_key: str) -> bool:
    """缓存的 API Key 检查（提高性能）。"""
    return api_key in security_config.API_KEYS


def verify_api_key(
    api_key: str = Security(API_KEY_HEADER),
) -> Optional[str]:
    """
    验证 API Key。

    Args:
        api_key: 从请求头获取的 API Key

    Returns:
        有效的 API Key

    Raises:
        HTTPException: 认证失败
    """
    if not api_key:
        return None

    # 清理 API Key（去除空白字符）
    api_key = api_key.strip()

    if not _cached_api_key_check(api_key):
        _log_audit(
            action="api_key_auth",
            user_type="api_key",
            identifier=api_key[:8] + "..." if len(api_key) > 8 else api_key,
            success=False,
            reason="invalid_key",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key",
            headers={"WWW-Authenticate": "API-Key"},
        )

    _log_audit(
        action="api_key_auth",
        user_type="api_key",
        identifier=api_key[:8] + "..." if len(api_key) > 8 else api_key,
        success=True,
    )
    return api_key


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    创建 JWT Access Token。

    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量

    Returns:
        JWT Token 字符串
        
    Raises:
        ValueError: 当密钥配置无效时
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=security_config.JWT_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})

    # 验证密钥配置
    if not security_config.JWT_SECRET_KEY or security_config.JWT_SECRET_KEY.startswith("your-secret"):
        logger.warning("使用默认 JWT 密钥，生产环境必须修改！")

    encoded_jwt = jwt.encode(
        to_encode,
        security_config.JWT_SECRET_KEY,
        algorithm=security_config.JWT_ALGORITHM,
    )

    return encoded_jwt


def verify_token(token: str = Security(oauth2_scheme)) -> Optional[TokenData]:
    """
    验证 JWT Token。

    Args:
        token: JWT Token

    Returns:
        TokenData 或 None

    Raises:
        HTTPException: 认证失败
    """
    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            security_config.JWT_SECRET_KEY,
            algorithms=[security_config.JWT_ALGORITHM],
        )

        username: str = payload.get("sub")
        api_key: str = payload.get("api_key")
        scopes: list = payload.get("scopes", [])
        exp_timestamp: int = payload.get("exp")
        
        exp_datetime = None
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

        if username is None and api_key is None:
            _log_audit(
                action="jwt_auth",
                user_type="jwt",
                identifier="unknown",
                success=False,
                reason="missing_subject",
            )
            return None

        _log_audit(
            action="jwt_auth",
            user_type="jwt",
            identifier=username or api_key[:8] + "...",
            success=True,
        )

        return TokenData(
            username=username, 
            api_key=api_key, 
            scopes=scopes,
            exp=exp_datetime
        )

    except ExpiredSignatureError:
        _log_audit(
            action="jwt_auth",
            user_type="jwt",
            identifier="expired_token",
            success=False,
            reason="token_expired",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        _log_audit(
            action="jwt_auth",
            user_type="jwt",
            identifier="invalid_token",
            success=False,
            reason=f"jwt_error: {str(e)}",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    api_key: Optional[str] = Depends(verify_api_key),
    token_data: Optional[TokenData] = Depends(verify_token),
) -> dict:
    """
    获取当前认证用户。

    支持两种认证方式：
    1. API Key (X-API-Key 请求头)
    2. JWT Bearer Token (Authorization 请求头)

    Args:
        request: FastAPI 请求对象（用于获取 IP）
        api_key: API Key
        token_data: JWT Token 数据

    Returns:
        用户信息字典

    Raises:
        HTTPException: 认证失败
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # 优先使用 API Key 认证
    if api_key:
        return {
            "type": "api_key", 
            "key": api_key[:8] + "...",  # 脱敏显示
            "ip": client_ip
        }

    # 其次使用 JWT 认证
    if token_data:
        return {
            "type": "jwt",
            "username": token_data.username,
            "api_key": token_data.api_key[:8] + "..." if token_data.api_key else None,
            "scopes": token_data.scopes,
            "exp": token_data.exp,
            "ip": client_ip
        }

    # 两种认证都失败
    _log_audit(
        action="auth_required",
        user_type="unknown",
        identifier="anonymous",
        success=False,
        reason="no_credentials",
        ip_address=client_ip,
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="需要提供有效的认证凭证（API Key 或 JWT Token）",
        headers={"WWW-Authenticate": "API-Key, Bearer"},
    )


# 可选认证装饰器（不强制要求认证，但如果有则验证）
async def get_optional_user(
    request: Request,
    api_key: Optional[str] = Depends(verify_api_key),
    token_data: Optional[TokenData] = Depends(verify_token),
) -> Optional[dict]:
    """
    获取可选的当前用户（认证失败时返回 None 而不是抛出异常）。

    用于部分公开、部分受限的端点。
    """
    client_ip = request.client.host if request.client else "unknown"
    
    if api_key:
        return {
            "type": "api_key", 
            "key": api_key[:8] + "...",
            "ip": client_ip
        }

    if token_data:
        return {
            "type": "jwt",
            "username": token_data.username,
            "api_key": token_data.api_key[:8] + "..." if token_data.api_key else None,
            "scopes": token_data.scopes,
            "ip": client_ip
        }

    return None
