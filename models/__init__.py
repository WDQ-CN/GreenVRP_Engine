# Models Module
"""
SQLAlchemy ORM 模型模块

提供数据库持久化支持。
"""

from .customer import Customer
from .database import Base, SessionLocal, engine, get_db
from .scenario import Scenario
from .solution import Solution
from .vehicle_config import VehicleConfig

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "Scenario",
    "Customer",
    "Solution",
    "VehicleConfig",
]
