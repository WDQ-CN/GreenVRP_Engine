"""
API 依赖注入模块

集中管理 FastAPI 应用的依赖注入关系。
使测试可轻松使用 dependency_overrides 替换具体实现。
"""

import logging
from collections.abc import Generator

from sqlalchemy.orm import Session as DBSession

# 全局 SolverService 单例（默认使用内存 JobManager）
from api.services.solver_service import SolverService
from core.interfaces import ISolverService
from models.database import get_db as _get_db

logger = logging.getLogger(__name__)

_solver_service: ISolverService | None = None


def get_solver_service() -> ISolverService:
    """
    获取求解器服务实例（单例）。

    返回 SolverService 实例，测试时可通过
    `app.dependency_overrides[get_solver_service]` 替换为 Mock。
    """
    global _solver_service
    if _solver_service is None:
        _solver_service = SolverService()
        logger.info("SolverService 实例已创建（单例）")
    else:
        logger.debug("复用 SolverService 单例")
    return _solver_service


def reset_solver_service() -> None:
    """重置求解器服务实例（主要用于测试）。"""
    global _solver_service
    if _solver_service is not None:
        logger.info("SolverService 实例已重置")
    _solver_service = None


def get_db() -> Generator[DBSession, None, None]:
    """
    获取数据库会话（FastAPI 依赖注入用）。

    委托给 models.database 中的 get_db 实现。
    """
    yield from _get_db()
