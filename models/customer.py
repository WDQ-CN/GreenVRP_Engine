"""
客户 ORM 模型

存储场景中的客户数据。
"""

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .scenario import Scenario


class Customer(Base):
    """客户模型。"""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联场景
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("scenarios.id"), nullable=False, index=True, comment="所属场景ID"
    )
    scenario: Mapped["Scenario"] = relationship(back_populates="customers")

    # 客户数据
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="客户ID（0为仓库）")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="客户名称")
    lat: Mapped[float] = mapped_column(Float, nullable=False, comment="纬度")
    lon: Mapped[float] = mapped_column(Float, nullable=False, comment="经度")
    demand: Mapped[int] = mapped_column(Integer, default=0, comment="需求量")
    service_time_min: Mapped[int] = mapped_column(Integer, default=0, comment="服务时间（分钟）")
    tw_earliest: Mapped[int] = mapped_column(Integer, default=0, comment="时间窗最早")
    tw_latest: Mapped[int] = mapped_column(Integer, default=1440, comment="时间窗最晚")

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name='{self.name}', demand={self.demand})>"

    def to_dict(self) -> dict:
        """转换为字典（用于求解器输入）。"""
        return {
            "id": self.customer_id,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "demand": self.demand,
            "service_time_min": self.service_time_min,
            "tw_earliest": self.tw_earliest,
            "tw_latest": self.tw_latest,
        }
