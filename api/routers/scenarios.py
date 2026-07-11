"""
场景管理路由

提供场景 CRUD 操作。
"""

import threading
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import asc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Customer, Scenario, Solution, get_db

from ..schemas import (
    ScenarioCreate,
    ScenarioDetailResponse,
    ScenarioResponse,
    ScenarioUpdate,
)

router = APIRouter(prefix="/scenarios", tags=["场景管理"])

# 场景列表内存缓存：列表查询频繁且数据变化不频繁，短时缓存可显著降低 P95。
# 写操作（创建/更新/删除）会主动失效缓存，保证数据一致性。
# 缓存中存储字典列表，读取时重建 Pydantic 模型，既防污染又避免深拷贝开销。
_list_scenarios_cache: dict[tuple[int, int], tuple[float, list[dict[str, Any]]]] = {}
_scenarios_cache_lock = threading.Lock()
_SCENARIOS_CACHE_TTL_SECONDS = 30


def _serialize_scenarios(items: list[ScenarioResponse]) -> list[dict[str, Any]]:
    """将 ScenarioResponse 列表序列化为字典列表，避免缓存被外部修改。"""
    return [item.model_dump() for item in items]


def _deserialize_scenarios(payload: list[dict[str, Any]]) -> list[ScenarioResponse]:
    """反序列化字典列表为 ScenarioResponse 列表，返回全新对象以隔离调用方。"""
    return [ScenarioResponse(**d) for d in payload]


def _get_cached_scenarios(limit: int, offset: int) -> list[ScenarioResponse] | None:
    """读取场景列表缓存，过期自动清理。返回重建对象以避免调用方污染缓存。"""
    key = (limit, offset)
    now = time.time()
    with _scenarios_cache_lock:
        # 清理过期条目
        expired = [
            k
            for k, (ts, _) in _list_scenarios_cache.items()
            if now - ts > _SCENARIOS_CACHE_TTL_SECONDS
        ]
        for k in expired:
            del _list_scenarios_cache[k]
        entry = _list_scenarios_cache.get(key)
        if entry is None:
            return None
        return _deserialize_scenarios(entry[1])


def _set_cached_scenarios(limit: int, offset: int, value: list[ScenarioResponse]) -> None:
    """写入场景列表缓存。"""
    with _scenarios_cache_lock:
        _list_scenarios_cache[(limit, offset)] = (time.time(), _serialize_scenarios(value))


def _invalidate_scenarios_cache() -> None:
    """场景变更时失效全部列表缓存。"""
    with _scenarios_cache_lock:
        _list_scenarios_cache.clear()


@router.post(
    "",
    response_model=ScenarioResponse,
    summary="创建场景",
)
async def create_scenario(
    request: ScenarioCreate,
    db: Session = Depends(get_db),  # noqa: B008
) -> ScenarioResponse:
    """创建新场景。"""
    # 创建 Scenario 记录
    scenario = Scenario(
        name=request.name,
        description=request.description,
        vehicle_config_data=(
            {k: v.model_dump() for k, v in request.vehicle_config.items()}
            if request.vehicle_config
            else None
        ),
        params_data=request.params.model_dump() if request.params else None,
    )
    db.add(scenario)
    db.flush()  # 获取 scenario.id 但不提交，用于创建关联的 Customer

    # 创建关联的 Customer 记录
    for customer_data in request.customers:
        customer = Customer(
            scenario_id=scenario.id,
            customer_id=customer_data.id,
            name=customer_data.name,
            lat=customer_data.lat,
            lon=customer_data.lon,
            demand=customer_data.demand,
            service_time_min=customer_data.service_time_min,
            tw_earliest=customer_data.tw_earliest,
            tw_latest=customer_data.tw_latest,
        )
        db.add(customer)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"场景创建失败，数据冲突: {exc.orig}",
        ) from exc
    db.refresh(scenario)
    _invalidate_scenarios_cache()

    return ScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        customer_count=len(scenario.customers),
        solution_count=len(scenario.solutions),
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
    )


@router.get(
    "",
    response_model=list[ScenarioResponse],
    summary="列出场景",
)
async def list_scenarios(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[ScenarioResponse]:
    """列出所有场景（使用子查询聚合计数，避免加载完整关联对象）。"""
    cached = _get_cached_scenarios(limit, offset)
    if cached is not None:
        return cached

    # 子查询：统计每个场景的客户数与结果数，避免 joinedload 数据膨胀
    customer_counts = (
        db.query(Customer.scenario_id, func.count(Customer.id).label("cnt"))
        .group_by(Customer.scenario_id)
        .subquery()
    )
    solution_counts = (
        db.query(Solution.scenario_id, func.count(Solution.id).label("cnt"))
        .group_by(Solution.scenario_id)
        .subquery()
    )

    rows = (
        db.query(
            Scenario,
            func.coalesce(customer_counts.c.cnt, 0).label("customer_count"),
            func.coalesce(solution_counts.c.cnt, 0).label("solution_count"),
        )
        .outerjoin(customer_counts, customer_counts.c.scenario_id == Scenario.id)
        .outerjoin(solution_counts, solution_counts.c.scenario_id == Scenario.id)
        .order_by(asc(Scenario.updated_at).nullslast(), asc(Scenario.id))
        .offset(offset)
        .limit(limit)
        .all()
    )

    result = [
        ScenarioResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            customer_count=int(customer_count),
            solution_count=int(solution_count),
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s, customer_count, solution_count in rows
    ]
    _set_cached_scenarios(limit, offset, result)
    return result


@router.get(
    "/{scenario_id}",
    response_model=ScenarioDetailResponse,
    summary="获取场景详情",
)
async def get_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),  # noqa: B008
) -> ScenarioDetailResponse:
    """获取指定场景的详情，包含完整数据。"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail=f"场景不存在: {scenario_id}")

    # 将 Customer 对象转换为字典列表
    customers = [c.to_dict() for c in scenario.customers]

    return ScenarioDetailResponse(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        customers=customers,
        vehicle_config=scenario.vehicle_config_data,
        params=scenario.params_data,
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
    )


@router.put(
    "/{scenario_id}",
    response_model=ScenarioResponse,
    summary="更新场景",
)
async def update_scenario(
    scenario_id: int,
    request: ScenarioUpdate,
    db: Session = Depends(get_db),  # noqa: B008
) -> ScenarioResponse:
    """更新场景信息。"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail=f"场景不存在: {scenario_id}")

    # 更新基本字段
    if request.name is not None:
        scenario.name = request.name
    if request.description is not None:
        scenario.description = request.description

    # 更新车型配置
    if request.vehicle_config is not None:
        scenario.vehicle_config_data = {
            k: v.model_dump() for k, v in request.vehicle_config.items()
        }

    # 更新求解参数
    if request.params is not None:
        scenario.params_data = request.params.model_dump()

    # 更新客户数据：增量更新，对比差异后只变更变化的部分
    if request.customers is not None:
        existing_customers = {
            c.customer_id: c
            for c in db.query(Customer).filter(Customer.scenario_id == scenario_id).all()
        }
        incoming_ids = {c.id for c in request.customers}

        # 删除不再存在的客户
        for cust_id in set(existing_customers.keys()) - incoming_ids:
            db.delete(existing_customers[cust_id])

        # 新增或更新客户
        for customer_data in request.customers:
            if customer_data.id in existing_customers:
                # 更新现有客户
                cust = existing_customers[customer_data.id]
                cust.name = customer_data.name
                cust.lat = customer_data.lat
                cust.lon = customer_data.lon
                cust.demand = customer_data.demand
                cust.service_time_min = customer_data.service_time_min
                cust.tw_earliest = customer_data.tw_earliest
                cust.tw_latest = customer_data.tw_latest
            else:
                # 新增客户
                customer = Customer(
                    scenario_id=scenario_id,
                    customer_id=customer_data.id,
                    name=customer_data.name,
                    lat=customer_data.lat,
                    lon=customer_data.lon,
                    demand=customer_data.demand,
                    service_time_min=customer_data.service_time_min,
                    tw_earliest=customer_data.tw_earliest,
                    tw_latest=customer_data.tw_latest,
                )
                db.add(customer)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"场景更新失败，数据冲突: {exc.orig}",
        ) from exc
    db.refresh(scenario)
    _invalidate_scenarios_cache()

    return ScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        customer_count=len(scenario.customers),
        solution_count=len(scenario.solutions),
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
    )


@router.delete(
    "/{scenario_id}",
    summary="删除场景",
)
async def delete_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict:
    """删除指定场景。"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail=f"场景不存在: {scenario_id}")

    db.delete(scenario)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"场景删除失败，存在关联数据: {exc.orig}",
        ) from exc
    _invalidate_scenarios_cache()

    return {"message": f"场景 {scenario_id} 已删除"}
