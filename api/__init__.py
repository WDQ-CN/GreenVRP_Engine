# GreenVRP Engine API Module
"""
REST API 模块：提供标准化接口供外部系统集成

功能：
- 同步/异步求解端点
- 场景管理 CRUD
- WebSocket 实时推送
"""

from .main import app

__all__ = ["app"]
