"""
数据库配置

支持 SQLite（开发）和 PostgreSQL（生产）。
提供 DatabaseProvider 类（可实例化）和模块级便捷函数（向后兼容）。
"""

import logging
import os
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)


def _sanitize_db_url(url: str) -> str:
    """脱敏数据库 URL（隐藏密码）。"""
    if "@" in url:
        # postgresql://user:password@host:port/db → postgresql://user:***@host:port/db
        scheme_rest, host_part = url.split("@", 1)
        if ":" in scheme_rest:
            scheme, _ = scheme_rest.rsplit(":", 1)
            return f"{scheme}:***@{host_part}"
    return url


class DatabaseProvider:
    """数据库提供者（可实例化，支持依赖注入）。

    封装了 SQLAlchemy 引擎和会话工厂的创建逻辑，
    支持 SQLite 和 PostgreSQL 的自动配置。

    Example:
        >>> provider = DatabaseProvider("sqlite:///:memory:")
        >>> db = next(provider.get_db())
        >>> provider.init_db()
    """

    def __init__(self, database_url: str | None = None):
        """
        初始化数据库提供者。

        Args:
            database_url: 数据库 URL，默认为环境变量 DATABASE_URL
                        或 "sqlite:///./green_vrp.db"
        """
        self._database_url: str = (
            database_url or os.getenv("DATABASE_URL") or "sqlite:///./green_vrp.db"
        )
        self._is_sqlite = self._database_url.startswith("sqlite")

        logger.info(
            "DatabaseProvider 初始化: url=%s",
            _sanitize_db_url(self._database_url),
        )

        # 构建连接参数
        connect_args: dict[str, Any] = {}
        pool_args: dict[str, Any] = {}

        if self._is_sqlite:
            # SQLite 在 FastAPI 的线程池环境中需要显式关闭 check_same_thread。
            # 配合 StaticPool（单连接 + SQLAlchemy 内部锁）可避免 QueuePool 多连接复用导致的数据损坏风险。
            # 生产环境建议切换为 PostgreSQL，彻底规避 SQLite 的线程模型限制。
            connect_args["check_same_thread"] = False
            pool_args["poolclass"] = StaticPool
        else:
            pool_args["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
            pool_args["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))

        self._engine = create_engine(
            self._database_url,
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            connect_args=connect_args,
            **pool_args,
        )

        self._session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine,
        )

        self.Base = declarative_base()

    def get_db(self) -> Generator[Session, None, None]:
        """
        获取数据库会话。

        使用方式：
            @app.get("/items")
            def get_items(db: Session = Depends(provider.get_db)):
                ...

        Yields:
            SQLAlchemy Session
        """
        db = self._session_local()
        logger.debug("数据库会话已创建: id=%s", id(db))
        try:
            yield db
        except Exception:
            db.rollback()
            logger.warning("数据库会话回滚: id=%s", id(db))
            raise
        finally:
            db.close()
            logger.debug("数据库会话已关闭: id=%s", id(db))

    def init_db(self) -> None:
        """初始化数据库（创建所有表）。"""
        logger.info("正在初始化数据库表...")
        self.Base.metadata.create_all(bind=self._engine)
        logger.info("数据库表初始化完成")

    def drop_db(self) -> None:
        """删除所有表（谨慎使用）。"""
        logger.warning("正在删除所有数据库表...")
        self.Base.metadata.drop_all(bind=self._engine)
        logger.warning("数据库表已删除")


# ============================================================
# 向后兼容：保留模块级便捷函数和全局实例
# 新代码推荐使用 DatabaseProvider 实例化方式
# ============================================================

# 默认全局实例
_default_provider = DatabaseProvider()

# 导出便捷引用（保持与旧代码兼容）
engine = _default_provider._engine
SessionLocal = _default_provider._session_local
Base = _default_provider.Base


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（向后兼容的模块级函数）。"""
    yield from _default_provider.get_db()


def init_db() -> None:
    """初始化数据库（向后兼容的模块级函数）。"""
    _default_provider.init_db()


def drop_db() -> None:
    """删除所有表（向后兼容的模块级函数）。"""
    _default_provider.drop_db()
