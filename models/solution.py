"""
求解结果 ORM 模型

存储求解结果和成本数据。
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .scenario import Scenario


class Solution(Base):
    """求解结果模型。"""

    __tablename__ = "solutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联场景
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("scenarios.id"), nullable=False, comment="所属场景ID"
    )
    scenario: Mapped["Scenario"] = relationship(back_populates="solutions")

    # 任务信息
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="任务ID")
    status: Mapped[str] = mapped_column(String(32), default="pending", comment="任务状态")

    # 求解结果（JSON 存储）
    solution_data: Mapped[Optional[dict]] = mapped_column(JSON, comment="求解结果数据")
    cost_data: Mapped[Optional[dict]] = mapped_column(JSON, comment="成本数据")

    # 关键指标（便于查询和排序）
    total_distance: Mapped[float] = mapped_column(Float, default=0.0, comment="总距离（公里）")
    total_cost: Mapped[float] = mapped_column(Float, default=0.0, comment="总成本（元）")
    carbon_emission_kg: Mapped[float] = mapped_column(Float, default=0.0, comment="碳排放量（kg）")
    solve_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, comment="求解耗时（秒）")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="开始时间")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="完成时间")

    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), comment="错误信息")

    def __repr__(self) -> str:
        return f"<Solution(id={self.id}, job_id='{self.job_id}', status='{self.status}')>"

    def is_completed(self) -> bool:
        """是否已完成。"""
        return self.status == "completed"

    def is_failed(self) -> bool:
        """是否失败。"""
        return self.status == "failed"
