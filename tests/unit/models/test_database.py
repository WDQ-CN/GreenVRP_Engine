"""数据库配置回归测试。"""

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import text
from sqlalchemy.pool import StaticPool

from models.database import DatabaseProvider


class TestDatabaseProviderSQLite:
    """验证 SQLite 配置的线程安全性回归。"""

    def test_sqlite_uses_static_pool(self):
        """SQLite 必须使用 StaticPool，以单连接 + 内部锁避免多线程数据竞争。"""
        provider = DatabaseProvider("sqlite:///:memory:")
        assert provider._engine.dialect.name == "sqlite"
        assert isinstance(provider._engine.pool, StaticPool)

    def test_sqlite_is_thread_safe_under_static_pool(self):
        """验证 StaticPool 下的 SQLite 可在多线程环境安全访问。"""
        provider = DatabaseProvider("sqlite:///:memory:")

        def _touch_db():
            with provider._engine.connect() as conn:
                return conn.scalar(text("SELECT 1"))

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: _touch_db(), range(8)))
        assert all(r == 1 for r in results)
