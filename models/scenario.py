"""
场景 ORM 模型

存储求解场景的基本信息。
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, desc
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .customer import Customer
    from .solution import Solution
    from .vehicle_config import VehicleConfig


class Scenario(Base):
    """场景模型。"""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="场景名称")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="场景描述")

    # 关联车型配置
    vehicle_config_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vehicle_configs.id"), comment="车型配置ID"
    )
    vehicle_config: Mapped[Optional["VehicleConfig"]] = relationship(back_populates="scenarios")

    # 关联客户
    customers: Mapped[List["Customer"]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
        order_by="Customer.id",
    )

    # 关联求解结果
    solutions: Mapped[List["Solution"]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
        order_by="Solution.created_at.desc()",  # 字符串形式在懒加载时由 SQLAlchemy 解析
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=lambda: datetime.now(timezone.utc), comment="更新时间"
    )

    def __repr__(self) -> str:
        return f"<Scenario(id={self.id}, name='{self.name}')>"
