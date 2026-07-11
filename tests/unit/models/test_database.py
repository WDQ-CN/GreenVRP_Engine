"""
单元测试：models/database.py — 数据库配置
"""

from sqlalchemy import text


class TestDatabaseEngine:
    def test_create_tables(self, fresh_db):
        """表创建后应可查询。"""
        result = fresh_db.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ))
        tables = [row[0] for row in result]
        assert len(tables) > 0  # ORM 模型表

    def test_get_db_yields_session(self):
        """get_db 应产生会话对象。"""
        from models.database import get_db
        gen = get_db()
        db = next(gen)
        assert db is not None
        try:
            next(gen)
        except StopIteration:
            pass
        finally:
            db.close()
