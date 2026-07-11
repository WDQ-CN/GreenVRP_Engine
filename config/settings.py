"""
全局设置模块

管理应用程序的全局配置。
"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """应用程序设置。"""

    # 应用信息
    app_name: str = "GreenVRP Engine"
    app_version: str = "1.0.0"
    debug: bool = False

    # API 设置
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    allowed_origins: list[str] = field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8501"]
    )

    # 求解器设置
    default_time_limit_seconds: int = 60
    max_time_limit_seconds: int = 300

    # 日志设置
    log_level: str = "INFO"
    log_file: str | None = None

    # 缓存设置
    distance_cache_max_size: int = 1000

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量创建设置。"""
        origins_env = os.getenv("GREENVRP_ALLOWED_ORIGINS", "")
        allowed_origins = (
            [o.strip() for o in origins_env.split(",") if o.strip()]
            if origins_env
            else ["http://localhost:3000", "http://localhost:8501"]
        )
        return cls(
            debug=os.getenv("GREENVRP_DEBUG", "false").lower() == "true",
            api_host=os.getenv("GREENVRP_API_HOST", "127.0.0.1"),
            api_port=int(os.getenv("GREENVRP_API_PORT", "8000")),
            allowed_origins=allowed_origins,
            log_level=os.getenv("GREENVRP_LOG_LEVEL", "INFO"),
            log_file=os.getenv("GREENVRP_LOG_FILE"),
        )


# 全局设置实例
_settings: Settings | None = None


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
