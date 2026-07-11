"""
OAuth2 认证路由

提供令牌获取端点，支持密码模式认证。
"""

import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from api.security.auth import (
    TokenData,
    create_access_token,
    verify_api_key,
    verify_token,
)
from config.security import security_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["认证"])


@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> dict:
    """
    OAuth2 密码模式令牌获取。

    使用用户名（API Key）和密码（留空）获取 JWT 访问令牌。
    也支持仅使用 API Key（X-API-Key 头）的认证方式。
    """
    # 验证用户凭证 — API Key 作为用户名
    api_key = form_data.username.strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查 API Key 是否有效
    if api_key not in security_config.API_KEYS:
        logger.warning(f"无效的 API Key 尝试: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key 无效",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建访问令牌
    access_token_expires = timedelta(minutes=security_config.JWT_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": api_key, "scopes": ["solver"]},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": security_config.JWT_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/verify")
async def verify_current_token(
    current_user: Optional[TokenData] = Depends(verify_token),
) -> dict:
    """验证当前令牌是否有效。"""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
        )
    return {
        "valid": True,
        "username": current_user.username,
        "scopes": current_user.scopes,
    }
