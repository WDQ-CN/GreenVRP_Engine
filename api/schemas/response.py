"""
API 响应模型定义

定义所有 API 返回的数据结构。
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class StopData(BaseModel):
    """站点数据。"""

    node: int = Field(..., description="节点索引")
    customer_id: Optional[int] = Field(default=None, description="客户ID（仓库终点为None）")
    customer_name: str = Field(..., description="客户名称")
    lat: float = Field(..., description="纬度")
    lon: float = Field(..., description="经度")
    demand: int = Field(default=0, description="需求量")
    arrival_time: Optional[int] = Field(default=None, description="到达时间（分钟）")
    departure_time: Optional[int] = Field(default=None, description="离开时间（分钟）")
    service_time: int = Field(default=0, description="服务时间（分钟）")
    tw_earliest: int = Field(default=0, description="时间窗最早")
    tw_latest: int = Field(default=0, description="时间窗最晚")
    late_minutes: int = Field(default=0, description="迟到分钟数")
    is_late: bool = Field(default=False, description="是否迟到")


class RouteData(BaseModel):
    """路线数据。"""

    vehicle_id: int = Field(..., description="车辆ID")
    vehicle_type: str = Field(..., description="车型")
    vehicle_color: str = Field(default="#1f77b4", description="颜色")
    capacity: int = Field(..., description="载重容量")
    stops: List[StopData] = Field(default_factory=list, description="站点列表")
    distance_km: float = Field(default=0.0, description="行驶距离（公里）")
    total_demand: int = Field(default=0, description="总需求量")
    total_time_min: float = Field(default=0.0, description="总时间（分钟）")
    late_minutes: int = Field(default=0, description="迟到分钟数")


class SolutionData(BaseModel):
    """求解结果数据。"""

    routes: List[RouteData] = Field(default_factory=list, description="路线列表")
    total_distance: float = Field(default=0.0, description="总距离（公里）")
    vehicles_used: Dict[str, int] = Field(default_factory=dict, description="各车型使用数量")
    total_late_minutes: int = Field(default=0, description="总迟到分钟数")
    solution_status: str = Field(default="UNKNOWN", description="求解状态")
    solve_time_seconds: float = Field(default=0.0, description="求解耗时（秒）")


class CostData(BaseModel):
    """成本数据。"""

    transport_cost: float = Field(default=0.0, description="运输变动成本")
    labor_cost: float = Field(default=0.0, description="人工时间成本")
    fixed_cost: float = Field(default=0.0, description="车辆固定成本")
    penalty_cost: float = Field(default=0.0, description="违约惩罚成本")
    carbon_cost: float = Field(default=0.0, description="碳排放成本")
    total_cost: float = Field(default=0.0, description="总成本")
    carbon_emission_kg: float = Field(default=0.0, description="碳排放量（kg）")
    total_distance_km: float = Field(default=0.0, description="总距离（公里）")
    total_time_min: float = Field(default=0.0, description="总时间（分钟）")
    driving_time_min: float = Field(default=0.0, description="行驶时间")
    service_time_min: float = Field(default=0.0, description="服务时间")
    waiting_time_min: float = Field(default=0.0, description="等待时间")
    cost_breakdown: Dict[str, float] = Field(default_factory=dict, description="成本明细")


class SolveResponse(BaseModel):
    """求解响应模型。"""

    job_id: str = Field(..., description="任务ID")
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        ..., description="任务状态"
    )
    solution: Optional[SolutionData] = Field(default=None, description="求解结果")
    cost_result: Optional[CostData] = Field(default=None, description="成本结果")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    error_message: Optional[str] = Field(default=None, description="错误信息")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "abc123",
                    "status": "completed",
                    "solution": {
                        "routes": [],
                        "total_distance": 100.5,
                        "vehicles_used": {"4.2m": 2},
                        "total_late_minutes": 0,
                        "solution_status": "SUCCESS",
                        "solve_time_seconds": 5.2,
                    },
                    "cost_result": {
                        "total_cost": 1500.0,
                        "carbon_emission_kg": 25.5,
                    },
                    "created_at": "2024-01-01T10:00:00",
                    "completed_at": "2024-01-01T10:00:05",
                }
            ]
        }
    }


class JobStatusResponse(BaseModel):
    """任务状态响应。"""

    job_id: str = Field(..., description="任务ID")
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        ..., description="任务状态"
    )
    progress: Optional[int] = Field(default=None, ge=0, le=100, description="进度百分比")
    message: Optional[str] = Field(default=None, description="状态消息")
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")


class ScenarioResponse(BaseModel):
    """场景响应模型。"""

    id: int = Field(..., description="场景ID")
    name: str = Field(..., description="场景名称")
    description: Optional[str] = Field(default=None, description="场景描述")
    customer_count: int = Field(default=0, description="客户数量")
    solution_count: int = Field(default=0, description="求解结果数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: Literal["healthy", "unhealthy"] = Field(..., description="健康状态")
    version: str = Field(default="2.0.0", description="API版本")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    components: Dict[str, str] = Field(
        default_factory=lambda: {"database": "ok", "solver": "ok"}, description="组件状态"
    )
