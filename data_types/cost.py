"""
成本类型定义

定义成本计算相关的数据类型。
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class CostBreakdown:
    """
    成本明细数据类。

    Attributes:
        transport_cost: 运输成本
        fixed_cost: 固定成本
        labor_cost: 人工成本
        carbon_cost: 碳排放成本
        penalty_cost: 罚金成本
    """

    transport_cost: float = 0.0
    fixed_cost: float = 0.0
    labor_cost: float = 0.0
    carbon_cost: float = 0.0
    penalty_cost: float = 0.0

    @property
    def total_cost(self) -> float:
        """计算总成本。"""
        return (
            self.transport_cost
            + self.fixed_cost
            + self.labor_cost
            + self.carbon_cost
            + self.penalty_cost
        )

    def to_dict(self) -> Dict[str, float]:
        """转换为字典。"""
        return {
            "transport_cost": self.transport_cost,
            "fixed_cost": self.fixed_cost,
            "labor_cost": self.labor_cost,
            "carbon_cost": self.carbon_cost,
            "penalty_cost": self.penalty_cost,
            "total_cost": self.total_cost,
        }


@dataclass
class CostResult:
    """
    成本计算结果数据类。

    Attributes:
        breakdown: 成本明细
        carbon_emission_kg: 碳排放量（kg CO2）
        total_distance_km: 总距离（公里）
        total_time_min: 总时间（分钟）
        vehicle_count: 车辆数
        efficiency_metrics: 效率指标
    """

    breakdown: CostBreakdown = field(default_factory=CostBreakdown)
    carbon_emission_kg: float = 0.0
    total_distance_km: float = 0.0
    total_time_min: float = 0.0
    vehicle_count: int = 0
    efficiency_metrics: Dict[str, float] = field(default_factory=dict)

    @property
    def total_cost(self) -> float:
        """获取总成本。"""
        return self.breakdown.total_cost

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            **self.breakdown.to_dict(),
            "carbon_emission_kg": self.carbon_emission_kg,
            "total_distance_km": self.total_distance_km,
            "total_time_min": self.total_time_min,
            "vehicle_count": self.vehicle_count,
            "efficiency_metrics": self.efficiency_metrics,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostResult":
        """从字典创建实例。"""
        breakdown = CostBreakdown(
            transport_cost=data.get("transport_cost", 0.0),
            fixed_cost=data.get("fixed_cost", 0.0),
            labor_cost=data.get("labor_cost", 0.0),
            carbon_cost=data.get("carbon_cost", 0.0),
            penalty_cost=data.get("penalty_cost", 0.0),
        )
        return cls(
            breakdown=breakdown,
            carbon_emission_kg=data.get("carbon_emission_kg", 0.0),
            total_distance_km=data.get("total_distance_km", 0.0),
            total_time_min=data.get("total_time_min", 0.0),
            vehicle_count=data.get("vehicle_count", 0),
            efficiency_metrics=data.get("efficiency_metrics", {}),
        )


@dataclass
class CarbonEfficiency:
    """
    碳效率指标数据类。

    Attributes:
        total_carbon_kg: 总碳排放（kg CO2）
        carbon_per_km: 单位距离碳排放（kg/km）
        carbon_per_customer: 单位客户碳排放（kg/客户）
        carbon_per_kg_demand: 单位需求碳排放（kg/kg）
    """

    total_carbon_kg: float = 0.0
    carbon_per_km: float = 0.0
    carbon_per_customer: float = 0.0
    carbon_per_kg_demand: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """转换为字典。"""
        return {
            "total_carbon_kg": self.total_carbon_kg,
            "carbon_per_km": self.carbon_per_km,
            "carbon_per_customer": self.carbon_per_customer,
            "carbon_per_kg_demand": self.carbon_per_kg_demand,
        }
