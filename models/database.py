"""
数据库配置

支持 SQLite（开发）和 PostgreSQL（生产）。
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# 数据库 URL 配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./green_vrp.db")  # 默认使用 SQLite

# 连接池配置
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))  # 连接池大小
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "40"))  # 最大溢出连接数
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 连接回收时间（秒）
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"  # 连接前检查

# 创建引擎
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}
    
# SQLite 使用 NullPool（不维护连接池），PostgreSQL 使用 QueuePool
_is_sqlite = "sqlite" in DATABASE_URL

if _is_sqlite:
    from sqlalchemy.pool import NullPool

    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args=connect_args,
        poolclass=NullPool,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_recycle=POOL_RECYCLE,
        pool_pre_ping=POOL_PRE_PING,
    )

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（FastAPI 依赖注入用）。

    使用方式：
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """初始化数据库（创建所有表）。"""
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """删除所有表（谨慎使用）。"""
    Base.metadata.drop_all(bind=engine)
