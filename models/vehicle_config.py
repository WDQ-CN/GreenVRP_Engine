"""
车型配置 ORM 模型

存储可用的车型参数。
"""

from typing import TYPE_CHECKING

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .scenario import Scenario


class VehicleConfig(Base):
    """车型配置模型。"""

    __tablename__ = "vehicle_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="车型名称")

    # 车型参数
    capacity: Mapped[int] = mapped_column(Integer, default=0, comment="载重容量（件）")
    fixed_cost: Mapped[float] = mapped_column(Float, default=0.0, comment="发车成本（元）")
    fuel_per_100km: Mapped[float] = mapped_column(Float, default=12.0, comment="百公里油耗（升）")
    speed_kmh: Mapped[float] = mapped_column(Float, default=40.0, comment="平均速度（km/h）")
    count: Mapped[int] = mapped_column(Integer, default=1, comment="可用数量")
    color: Mapped[str] = mapped_column(String(20), default="#1f77b4", comment="显示颜色")

    # 关联场景
    scenarios: Mapped[list["Scenario"]] = relationship(back_populates="vehicle_config")

    def __repr__(self) -> str:
        return f"<VehicleConfig(id={self.id}, name='{self.name}', capacity={self.capacity})>"

    def to_dict(self) -> dict:
        """转换为字典（用于求解器输入）。"""
        return {
            "capacity": self.capacity,
            "fixed_cost": self.fixed_cost,
            "fuel_per_100km": self.fuel_per_100km,
            "speed_kmh": self.speed_kmh,
            "count": self.count,
            "color": self.color,
        }


def get_default_vehicle_configs() -> dict:
    """获取默认车型配置（引用 config/vehicles.py 避免数据重复）。"""
    from config.vehicles import DEFAULT_VEHICLE_CONFIG

    return DEFAULT_VEHICLE_CONFIG
