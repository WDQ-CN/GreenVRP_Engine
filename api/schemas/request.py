"""
API 请求模型定义

使用 Pydantic 进行数据验证和序列化。
"""

from pydantic import BaseModel, Field, model_validator


class CustomerData(BaseModel):
    """客户数据模型。"""

    id: int = Field(..., ge=0, description="客户ID，0为仓库")
    name: str = Field(..., min_length=1, max_length=100, description="客户名称")
    lat: float = Field(..., ge=-90, le=90, description="纬度")
    lon: float = Field(..., ge=-180, le=180, description="经度")
    demand: int = Field(..., ge=0, description="需求量（件）")
    service_time_min: int = Field(..., ge=0, description="服务时间（分钟）")
    tw_earliest: int = Field(..., ge=0, le=1440, description="时间窗开始（分钟，0:00起）")
    tw_latest: int = Field(..., ge=0, le=1440, description="时间窗结束（分钟，0:00起）")

    @model_validator(mode="after")
    def validate_time_window(self):
        """验证时间窗开始时间不晚于结束时间。"""
        if self.tw_earliest > self.tw_latest:
            raise ValueError("tw_earliest 必须 <= tw_latest")
        return self


class VehicleConfigItem(BaseModel):
    """车型配置项。"""

    capacity: int = Field(..., ge=0, description="载重容量（件）")
    fixed_cost: float = Field(..., ge=0, description="发车成本（元）")
    fuel_per_100km: float = Field(..., ge=0, description="百公里油耗（升）")
    speed_kmh: float = Field(..., gt=0, description="平均速度（km/h）")
    count: int = Field(..., ge=0, description="可用数量")
    color: str = Field(default="#1f77b4", description="显示颜色")


class SolverParams(BaseModel):
    """求解器参数。"""

    fuel_price: float = Field(default=7.5, ge=0, description="油价（元/升）")
    hourly_wage: float = Field(default=50.0, ge=0, description="时薪（元/小时）")
    carbon_price: float = Field(default=0.08, ge=0, description="碳交易价格（元/kg）")
    late_penalty_per_min: float = Field(default=10.0, ge=0, description="迟到罚金（元/分钟）")
    search_time_limit: int = Field(default=30, ge=1, le=600, description="求解时间限制（秒）")
    use_multi_strategy: bool = Field(default=True, description="启用多策略求解")
    use_parallel: bool = Field(default=True, description="启用并行求解")


class SolveRequest(BaseModel):
    """求解请求模型。"""

    customers: list[CustomerData] = Field(..., min_length=2, description="客户数据列表（含仓库）")
    vehicle_config: dict[str, VehicleConfigItem] | None = Field(
        default=None, description="车型配置，为空则使用默认配置"
    )
    params: SolverParams | None = Field(default=None, description="求解参数，为空则使用默认参数")
    callback_url: str | None = Field(default=None, description="异步求解完成后的回调URL")
    scenario_name: str | None = Field(
        default=None, max_length=255, description="场景名称，用于保存结果"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "customers": [
                        {
                            "id": 0,
                            "name": "仓库",
                            "lat": 39.9042,
                            "lon": 116.4074,
                            "demand": 0,
                            "service_time_min": 0,
                            "tw_earliest": 0,
                            "tw_latest": 1440,
                        },
                        {
                            "id": 1,
                            "name": "客户1",
                            "lat": 39.9142,
                            "lon": 116.4174,
                            "demand": 50,
                            "service_time_min": 15,
                            "tw_earliest": 480,
                            "tw_latest": 720,
                        },
                    ],
                    "params": {
                        "fuel_price": 7.5,
                        "search_time_limit": 30,
                    },
                }
            ]
        }
    }


class ScenarioCreate(BaseModel):
    """创建场景请求。"""

    name: str = Field(..., min_length=1, max_length=255, description="场景名称")
    description: str | None = Field(default=None, max_length=1000, description="场景描述")
    customers: list[CustomerData] = Field(..., min_length=2, description="客户数据")
    vehicle_config: dict[str, VehicleConfigItem] | None = Field(
        default=None, description="车型配置"
    )
    params: SolverParams | None = Field(default=None, description="求解参数")


class ScenarioUpdate(BaseModel):
    """更新场景请求。"""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    customers: list[CustomerData] | None = None
    vehicle_config: dict[str, VehicleConfigItem] | None = None
    params: SolverParams | None = Field(default=None, description="求解参数")
