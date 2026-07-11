"""
数据库接口模块

定义数据库提供者的接口契约，支持多种数据库实现（SQLite/PostgreSQL/测试内存库）。
"""

from collections.abc import Generator
from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session


@runtime_checkable
class IDatabaseProvider(Protocol):
    """数据库提供者接口。

    定义数据库会话管理的基本操作，支持 SQLite 和 PostgreSQL 等不同实现。
    """

    def get_db(self) -> Generator[Session, None, None]:
        """获取数据库会话（用于 FastAPI 依赖注入）。"""
        ...

    def init_db(self) -> None:
        """初始化数据库（创建所有表）。"""
        ...

    def drop_db(self) -> None:
        """删除所有表（谨慎使用）。"""
        ...
