"""
Pytest 全局配置与共享 fixtures。
"""

import os
import sys

import pytest

from api.dependencies import reset_solver_service

# 确保项目根目录在 PYTHONPATH 中（Windows spawn 子进程需要）
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

_original_pythonpath = os.environ.get("PYTHONPATH", "")
if project_root not in _original_pythonpath.split(os.pathsep):
    _sep = os.pathsep if _original_pythonpath else ""
    os.environ["PYTHONPATH"] = f"{_original_pythonpath}{_sep}{project_root}"

# 为测试提供默认 API Key，确保需要认证的接口在中间件初始化前即获得配置。
# 所有共享主应用实例的测试必须使用同一密钥，避免中间件缓存值与请求头不一致导致 401。
os.environ["GREENVRP_API_KEY"] = "test-api-key-12345"

# 测试期间禁用全局限流，避免多测试共享内存限流状态导致 429 误失败。
os.environ["GREENVRP_RATE_LIMIT_DISABLED"] = "true"

# 测试期间使用受信任来源，避免 CORS 中间件干扰。
os.environ.setdefault("GREENVRP_ALLOWED_ORIGINS", "http://localhost:3000")


@pytest.fixture(autouse=True)
def _reset_solver_service():
    """每个测试开始前重置 SolverService 单例，避免 lifespan 关闭后状态被后续测试复用。"""
    reset_solver_service()
    yield
