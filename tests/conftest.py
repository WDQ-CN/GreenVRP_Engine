"""
Pytest 全局配置与共享 fixtures。
"""

import os
import sys

import pytest

# 确保项目根目录在 PYTHONPATH 中（Windows spawn 子进程需要）
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

_original_pythonpath = os.environ.get("PYTHONPATH", "")
if project_root not in _original_pythonpath.split(os.pathsep):
    _sep = os.pathsep if _original_pythonpath else ""
    os.environ["PYTHONPATH"] = f"{_original_pythonpath}{_sep}{project_root}"

# 测试环境变量 — 在任何模块导入前设置
os.environ.setdefault("GREENVRP_API_KEY", "test-api-key-12345")
os.environ.setdefault("GREENVRP_RATE_LIMIT_DISABLED", "true")
os.environ.setdefault("GREENVRP_ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("API_KEYS", "test-api-key-12345,secondary-test-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-min-32-chars!!")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_green_vrp.db")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api_key() -> str:
    """默认测试 API Key。"""
    return "test-api-key-12345"


@pytest.fixture
def auth_headers(api_key: str) -> dict:
    """携带 API Key 的认证请求头。"""
    return {"X-API-Key": api_key}


@pytest.fixture
def fresh_db():
    """为每个测试提供干净的 SQLite 内存数据库。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from models.database import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_client():
    """FastAPI TestClient 实例（含认证中间件）。"""
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_solver_service(monkeypatch):
    """将 solver_service 替换为 MockSolverService。"""
    from tests.fixtures.mocks import MockSolverService

    mock_service = MockSolverService()
    monkeypatch.setattr("api.routers.solver.solver_service", mock_service)
    monkeypatch.setattr("api.services.solver_service.solver_service", mock_service)
    return mock_service


# ---------------------------------------------------------------------------
# Autouse fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_pycache():
    """每个测试前清理小规模缓存，避免导入缓存污染。"""
    # 仅清理特定模块的缓存（如果需要）
    yield


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch):
    """确保关键环境变量在测试中始终存在。"""
    monkeypatch.setenv("GREENVRP_RATE_LIMIT_DISABLED", "true")
    monkeypatch.setenv("GREENVRP_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("API_KEYS", "test-api-key-12345,secondary-test-key")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-testing-min-32-chars!!")
