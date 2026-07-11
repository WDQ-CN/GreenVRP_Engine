"""
全局设置模块

管理应用程序的全局配置。
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Settings:
    """应用程序设置。"""

    # 应用信息
    app_name: str = "GreenVRP Engine"
    app_version: str = "1.0.0"
    debug: bool = False

    # API 设置
    api_host: str = "0.0.0.0"  # nosec - 默认开发配置，可通过环境变量覆盖
    api_port: int = 8000

    # 求解器设置
    default_time_limit_seconds: int = 60
    max_time_limit_seconds: int = 300

    # 日志设置
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # 缓存设置
    distance_cache_max_size: int = 1000

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量创建设置。"""
        return cls(
            debug=os.getenv("GREENVRP_DEBUG", "false").lower() == "true",
            api_host=os.getenv("GREENVRP_API_HOST", "0.0.0.0"),  # nosec - 默认开发配置
            api_port=int(os.getenv("GREENVRP_API_PORT", "8000")),
            log_level=os.getenv("GREENVRP_LOG_LEVEL", "INFO"),
            log_file=os.getenv("GREENVRP_LOG_FILE"),
        )


# 全局设置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局设置实例。"""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def set_settings(settings: Settings) -> None:
    """设置全局设置实例。"""
    global _settings
    _settings = settings
