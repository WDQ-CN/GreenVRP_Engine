"""
场景管理路由

提供场景 CRUD 操作。
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from ..schemas import ScenarioCreate, ScenarioResponse, ScenarioUpdate
from ..security.auth import get_current_user
from ..security.rate_limit import limiter

router = APIRouter(prefix="/scenarios", tags=["场景管理"])

# 内存存储（生产环境应使用数据库）
_scenarios_db: dict = {}
_scenario_counter = 0


@router.post(
    "",
    response_model=ScenarioResponse,
    summary="创建场景",
)
@limiter.limit("20/minute")
async def create_scenario(
    request: Request,
    body: ScenarioCreate,
    current_user: dict = Depends(get_current_user),
) -> ScenarioResponse:
    """
    创建新场景。
    
    需要认证：是（API Key 或 JWT Token）
    速率限制：20/minute
    """
    global _scenario_counter
    _scenario_counter += 1

    scenario_id = _scenario_counter
    created_at = datetime.now()

    _scenarios_db[scenario_id] = {
        "id": scenario_id,
        "name": body.name,
        "description": body.description,
        "customers": [c.model_dump() for c in body.customers],
        "vehicle_config": (
            {k: v.model_dump() for k, v in body.vehicle_config.items()}
            if body.vehicle_config
            else None
        ),
        "created_at": created_at,
        "updated_at": None,
        "solutions": [],
    }

    return ScenarioResponse(
        id=scenario_id,
        name=body.name,
        description=body.description,
        customer_count=len(body.customers),
        solution_count=0,
        created_at=created_at,
    )


@router.get(
    "",
    response_model=List[ScenarioResponse],
    summary="列出场景",
)
@limiter.limit("100/minute")
async def list_scenarios(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
) -> List[ScenarioResponse]:
    """
    列出所有场景。
    
    需要认证：是（API Key 或 JWT Token）
    速率限制：100/minute
    """
    scenarios = list(_scenarios_db.values())[offset : offset + limit]

    return [
        ScenarioResponse(
            id=s["id"],
            name=s["name"],
            description=s.get("description"),
            customer_count=len(s.get("customers", [])),
            solution_count=len(s.get("solutions", [])),
            created_at=s["created_at"],
            updated_at=s.get("updated_at"),
        )
        for s in scenarios
    ]


@router.get(
    "/{scenario_id}",
    response_model=ScenarioResponse,
    summary="获取场景详情",
)
@limiter.limit("100/minute")
async def get_scenario(
    request: Request,
    scenario_id: int,
    current_user: dict = Depends(get_current_user),
) -> ScenarioResponse:
    """
    获取指定场景的详情。
    
    需要认证：是（API Key 或 JWT Token）
    速率限制：100/minute
    """
    if scenario_id not in _scenarios_db:
        raise HTTPException(status_code=404, detail=f"场景不存在：{scenario_id}")

    s = _scenarios_db[scenario_id]
    return ScenarioResponse(
        id=s["id"],
        name=s["name"],
        description=s.get("description"),
        customer_count=len(s.get("customers", [])),
        solution_count=len(s.get("solutions", [])),
        created_at=s["created_at"],
        updated_at=s.get("updated_at"),
    )


@router.put(
    "/{scenario_id}",
    response_model=ScenarioResponse,
    summary="更新场景",
)
@limiter.limit("20/minute")
async def update_scenario(
    request: Request,
    scenario_id: int,
    body: ScenarioUpdate,
    current_user: dict = Depends(get_current_user),
) -> ScenarioResponse:
    """
    更新场景信息。
    
    需要认证：是（API Key 或 JWT Token）
    速率限制：20/minute
    """
    if scenario_id not in _scenarios_db:
        raise HTTPException(status_code=404, detail=f"场景不存在：{scenario_id}")

    scenario = _scenarios_db[scenario_id]

    if body.name is not None:
        scenario["name"] = body.name
    if body.description is not None:
        scenario["description"] = body.description
    if body.customers is not None:
        scenario["customers"] = [c.model_dump() for c in body.customers]
    if body.vehicle_config is not None:
        scenario["vehicle_config"] = {k: v.model_dump() for k, v in body.vehicle_config.items()}

    scenario["updated_at"] = datetime.now()

    return ScenarioResponse(
        id=scenario_id,
        name=scenario["name"],
        description=scenario.get("description"),
        customer_count=len(scenario.get("customers", [])),
        solution_count=len(scenario.get("solutions", [])),
        created_at=scenario["created_at"],
        updated_at=scenario["updated_at"],
    )


@router.delete(
    "/{scenario_id}",
    summary="删除场景",
)
@limiter.limit("10/minute")
async def delete_scenario(
    request: Request,
    scenario_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    删除指定场景。
    
    需要认证：是（API Key 或 JWT Token）
    速率限制：10/minute
    """
    if scenario_id not in _scenarios_db:
        raise HTTPException(status_code=404, detail=f"场景不存在：{scenario_id}")

    del _scenarios_db[scenario_id]
    return {"message": f"场景 {scenario_id} 已删除"}
