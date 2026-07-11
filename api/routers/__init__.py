# API Routers Module
"""
FastAPI 路由模块
"""

from .auth import router as auth_router
from .health import router as health_router
from .scenarios import router as scenarios_router
from .solver import router as solver_router

__all__ = ["auth_router", "solver_router", "scenarios_router", "health_router"]
