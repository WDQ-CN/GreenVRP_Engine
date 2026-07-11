"""
场景 ORM 模型

存储求解场景的基本信息。
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .customer import Customer
    from .solution import Solution
    from .vehicle_config import VehicleConfig


class Scenario(Base):
    """场景模型。"""

    __tablename__ = "scenarios"

    # 复合索引：列表页按 updated_at 排序并分页
    __table_args__ = (Index("ix_scenarios_updated_at_id", "updated_at", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="场景名称")
    description: Mapped[str | None] = mapped_column(Text, comment="场景描述")

    # 关联车型配置（外键形式，保留向后兼容）
    vehicle_config_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicle_configs.id"), comment="车型配置ID"
    )
    vehicle_config: Mapped[Optional["VehicleConfig"]] = relationship(back_populates="scenarios")

    # 完整车型配置字典（直接存储前端/求解器使用的多车型配置）
    vehicle_config_data: Mapped[dict | None] = mapped_column(
        JSON, comment="多车型配置字典（key 为车型名称）"
    )

    # 求解参数
    params_data: Mapped[dict | None] = mapped_column(JSON, comment="求解参数")

    # 关联客户
    customers: Mapped[list["Customer"]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
        order_by="Customer.id",
    )

    # 关联求解结果
    solutions: Mapped[list["Solution"]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
        order_by="Solution.created_at.desc()",  # 字符串形式在懒加载时由 SQLAlchemy 解析
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=lambda: datetime.now(timezone.utc), comment="更新时间"
    )

    def __repr__(self) -> str:
        return f"<Scenario(id={self.id}, name='{self.name}')>"
