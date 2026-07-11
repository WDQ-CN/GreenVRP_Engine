"""
安全配置模块

包含 API 密钥、CORS 来源、回调 URL 白名单等安全配置。
生产环境应从环境变量加载这些配置。
"""

import os
import re
from typing import List, Set


class SecurityConfig:
    """安全配置类。"""

    # 环境标识
    ENV: str = os.getenv("GREENVRP_ENV", "development")

    # API 密钥配置 - 生产环境必须通过环境变量设置
    _api_keys_raw: str = os.getenv("API_KEYS", "")
    if not _api_keys_raw:
        if os.getenv("GREENVRP_ENV", "development") == "production":
            raise RuntimeError(
                "生产环境必须设置 API_KEYS 环境变量！"
            )
        _api_keys_raw = "green-vrp-default-key-2024"
        import logging
        logging.warning(
            "使用默认 API Key，仅限开发环境。生产环境请设置 API_KEYS 环境变量。"
        )
    API_KEYS: Set[str] = frozenset(
        key.strip() for key in filter(None, _api_keys_raw.split(","))
    )

    # JWT 配置（如果使用 JWT）
    _JWT_DEFAULT = "change-this-secret-key-in-production-min-32-chars"
    _jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", _JWT_DEFAULT)
    
    # 生产环境禁止使用默认密钥
    if _jwt_secret_key == _JWT_DEFAULT:
        if os.getenv("GREENVRP_ENV", "development") == "production":
            raise RuntimeError(
                "生产环境必须设置 JWT_SECRET_KEY 环境变量！"
            )
        import logging
        logging.warning(
            "使用默认 JWT 密钥，仅限开发环境。生产环境请设置 JWT_SECRET_KEY 环境变量。"
        )
    JWT_SECRET_KEY: str = _jwt_secret_key
    JWT_ALGORITHM: str = "HS256"
    JWT_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_TOKEN_EXPIRE_MINUTES", "60"))

    # CORS 配置 - 生产环境必须修改为实际的前端域名
    _allowed_origins_raw = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8501",
    )
    ALLOWED_ORIGINS: List[str] = [
        origin.strip() 
        for origin in filter(None, _allowed_origins_raw.split(","))
    ]

    # Callback URL 白名单 - 只允许特定域名接收回调
    _callback_whitelist_raw = os.getenv(
        "CALLBACK_URL_WHITELIST",
        "https://example.com/callback,https://api.example.com/webhook",
    )
    CALLBACK_URL_WHITELIST: List[str] = [
        url.strip() 
        for url in filter(None, _callback_whitelist_raw.split(","))
    ]

    # 允许的回调协议
    ALLOWED_CALLBACK_PROTOCOLS: Set[str] = frozenset(["https"])

    # 速率限制配置
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")
    RATE_LIMIT_SOLVER: str = os.getenv("RATE_LIMIT_SOLVER", "10/minute")
    RATE_LIMIT_UPLOAD: str = os.getenv("RATE_LIMIT_UPLOAD", "5/minute")

    # SSRF 防护：禁止的内网 CIDR
    BLOCKED_CIDRS: List[str] = [
        "10.0.0.0/8",      # 私有网络 A 类
        "172.16.0.0/12",   # 私有网络 B 类
        "192.168.0.0/16",  # 私有网络 C 类
        "127.0.0.0/8",     # 回环地址
        "169.254.0.0/16",  # 链路本地地址
        "0.0.0.0/8",       # 当前网络
    ]

    @classmethod
    def is_callback_url_allowed(cls, url: str) -> bool:
        """
        检查回调 URL 是否在白名单中。

        Args:
            url: 待检查的 URL

        Returns:
            是否允许
        """
        if not url:
            return False

        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)

            # 检查协议
            if parsed.scheme not in cls.ALLOWED_CALLBACK_PROTOCOLS:
                return False

            # 构建基础 URL 进行白名单匹配
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            # 检查是否在白名单中
            for allowed in cls.CALLBACK_URL_WHITELIST:
                allowed_parsed = urlparse(allowed)
                allowed_base = f"{allowed_parsed.scheme}://{allowed_parsed.netloc}"

                # 支持子路径匹配
                if base_url == allowed_base:
                    return True

                # 支持精确 URL 匹配
                if url == allowed:
                    return True

            return False

        except Exception:
            return False

    @classmethod
    def _is_private_ip(cls, ip: str) -> bool:
        """
        检查 IP 地址是否为私有地址或受保护地址。

        Args:
            ip: IP 地址字符串

        Returns:
            是否为受保护的 IP
        """
        import ipaddress

        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # 检查是否为私有、回环、链路本地地址
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                return True
            
            # 检查是否在 blocked CIDRs 中
            for cidr_str in cls.BLOCKED_CIDRS:
                cidr = ipaddress.ip_network(cidr_str, strict=False)
                if ip_obj in cidr:
                    return True
                    
            return False
        except ValueError:
            return True  # 无效的 IP 视为不安全

    @classmethod
    def validate_callback_url(cls, url: str) -> tuple[bool, str]:
        """
        验证回调 URL 的安全性。

        Args:
            url: 待验证的 URL

        Returns:
            (是否有效，错误消息)
        """
        if not url:
            return True, ""  # 空 URL 是允许的（可选回调）

        from urllib.parse import urlparse
        import socket

        # URL 格式预检查
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', 
            re.IGNORECASE
        )
        
        if not url_pattern.match(url):
            return False, "URL 格式不正确"

        try:
            parsed = urlparse(url)

            # 检查协议
            if parsed.scheme not in cls.ALLOWED_CALLBACK_PROTOCOLS:
                return (
                    False,
                    f"不支持的协议：{parsed.scheme}，仅允许 HTTPS",
                )

            # 检查主机名
            hostname = parsed.hostname
            if not hostname:
                return False, "无效的 URL 格式"

            # 阻止 localhost 和常见内部主机名
            if hostname.lower() in ('localhost', 'internal', 'admin'):
                return False, "不允许使用内部主机名作为回调地址"

            # 防止 DNS 重绑定攻击 - 解析并检查 IP
            try:
                # 获取所有 IP 地址（防止 DNS 轮询）
                addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET)
                for info in addr_info:
                    ip = info[4][0]
                    if cls._is_private_ip(ip):
                        return False, f"不允许使用内网 IP ({ip}) 作为回调地址"
            except socket.gaierror:
                return False, "无法解析主机名"
            except socket.error as e:
                return False, f"DNS 查询失败：{str(e)}"

            # 检查白名单
            if not cls.is_callback_url_allowed(url):
                return (
                    False,
                    "回调 URL 不在允许的白名单中",
                )

            return True, ""

        except Exception as e:
            return False, f"URL 验证失败：{str(e)}"

    @classmethod
    def validate_api_key_format(cls, api_key: str) -> tuple[bool, str]:
        """
        验证 API Key 格式是否符合要求。

        Args:
            api_key: 待验证的 API Key

        Returns:
            (是否有效，错误消息)
        """
        if not api_key:
            return False, "API Key 不能为空"
        
        if len(api_key) < 16:
            return False, "API Key 长度至少为 16 个字符"
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
            return False, "API Key 只能包含字母、数字、下划线和连字符"
        
        return True, ""

    @classmethod
    def get_security_headers(cls) -> dict:
        """
        获取推荐的安全响应头。

        Returns:
            安全头字典
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
        }


# 全局配置实例
security_config = SecurityConfig()
