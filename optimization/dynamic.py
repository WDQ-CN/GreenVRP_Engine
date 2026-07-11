"""
动态需求响应模块

处理实时事件（新增订单、取消订单、交通延误），
进行局部重优化以减少计算开销。
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from utils.geo import haversine_distance


class EventType(Enum):
    """动态事件类型。"""

    NEW_ORDER = "new_order"
    """新增订单"""

    CANCEL_ORDER = "cancel_order"
    """取消订单"""

    TRAFFIC_DELAY = "traffic_delay"
    """交通延误"""

    VEHICLE_BREAKDOWN = "vehicle_breakdown"
    """车辆故障"""

    CUSTOMER_CHANGE = "customer_change"
    """客户信息变更"""


@dataclass
class DynamicEvent:
    """动态事件数据类。"""

    event_type: EventType
    """事件类型"""

    timestamp: float
    """事件时间戳"""

    data: Dict[str, Any]
    """事件数据"""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DynamicEvent":
        """从字典创建。"""
        return cls(
            event_type=EventType(d["event_type"]),
            timestamp=d["timestamp"],
            data=d["data"],
        )


@dataclass
class ReoptimizationResult:
    """重优化结果。"""

    success: bool
    """是否成功"""

    old_solution: Dict[str, Any]
    """原解"""

    new_solution: Dict[str, Any]
    """新解"""

    changes: List[Dict[str, Any]]
    """变更列表"""

    cost_delta: float
    """成本变化"""

    reoptimization_time: float
    """重优化耗时"""

    affected_routes: List[int]
    """受影响的路线"""

    message: str = ""
    """消息"""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "success": self.success,
            "changes": self.changes,
            "cost_delta": self.cost_delta,
            "reoptimization_time": self.reoptimization_time,
            "affected_routes": self.affected_routes,
            "message": self.message,
        }


class DynamicReoptimizer:
    """动态重优化器。"""

    def __init__(
        self,
        solver_func,
        customers: List[Dict[str, Any]],
        vehicle_config: Dict[str, Dict[str, Any]],
        params: Dict[str, float],
    ):
        """
        初始化动态重优化器。

        Args:
            solver_func: 求解函数
            customers: 客户数据
            vehicle_config: 车型配置
            params: 全局参数
        """
        self.solver_func = solver_func
        self.base_customers = customers.copy()
        self.vehicle_config = vehicle_config
        self.params = params

        # 当前状态
        self.current_customers = customers.copy()
        self.current_solution = None
        self.current_positions = {}  # 车辆当前位置

        # 修复：维护递增的节点ID计数器，避免ID冲突
        max_id = max((c.get("id", 0) for c in customers), default=0)
        self._next_node_id = max_id + 1

    def set_current_solution(
        self,
        solution: Dict[str, Any],
    ) -> None:
        """
        设置当前解。

        Args:
            solution: 当前求解结果
        """
        self.current_solution = solution

    def set_vehicle_positions(
        self,
        positions: Dict[int, Tuple[float, float]],
    ) -> None:
        """
        设置车辆当前位置。

        Args:
            positions: 车辆ID到位置的映射
        """
        self.current_positions = positions

    def handle_event(
        self,
        event: DynamicEvent,
        current_solution: Optional[Dict[str, Any]] = None,
        full_reoptimize: bool = False,
    ) -> ReoptimizationResult:
        """
        处理动态事件。

        Args:
            event: 动态事件
            current_solution: 当前解（可选）
            full_reoptimize: 是否完全重优化

        Returns:
            ReoptimizationResult 重优化结果
        """
        if current_solution is not None:
            self.current_solution = current_solution

        if self.current_solution is None:
            return ReoptimizationResult(
                success=False,
                old_solution={},
                new_solution={},
                changes=[],
                cost_delta=0,
                reoptimization_time=0,
                affected_routes=[],
                message="无可用的当前解",
            )

        start_time = time.time()

        # 根据事件类型选择处理方法
        if event.event_type == EventType.NEW_ORDER:
            result = self._handle_new_order(event, full_reoptimize)
        elif event.event_type == EventType.CANCEL_ORDER:
            result = self._handle_cancel_order(event, full_reoptimize)
        elif event.event_type == EventType.TRAFFIC_DELAY:
            result = self._handle_traffic_delay(event, full_reoptimize)
        elif event.event_type == EventType.VEHICLE_BREAKDOWN:
            result = self._handle_vehicle_breakdown(event, full_reoptimize)
        else:
            result = ReoptimizationResult(
                success=False,
                old_solution=self.current_solution,
                new_solution=self.current_solution,
                changes=[],
                cost_delta=0,
                reoptimization_time=0,
                affected_routes=[],
                message=f"不支持的事件类型: {event.event_type}",
            )

        result.reoptimization_time = time.time() - start_time

        if result.success:
            self.current_solution = result.new_solution

        return result

    def _handle_new_order(
        self,
        event: DynamicEvent,
        full_reoptimize: bool,
    ) -> ReoptimizationResult:
        """
        处理新增订单事件。

        使用插入启发式将新客户插入到最合适的路线。
        """
        new_customer = event.data.get("customer")
        if not new_customer:
            return ReoptimizationResult(
                success=False,
                old_solution=self.current_solution,
                new_solution=self.current_solution,
                changes=[],
                cost_delta=0,
                reoptimization_time=0,
                affected_routes=[],
                message="缺少新客户数据",
            )

        # 修复：验证必要字段
        required_fields = ["id", "lat", "lon"]
        missing_fields = [
            f for f in required_fields if f not in new_customer or new_customer.get(f) is None
        ]
        if missing_fields:
            return ReoptimizationResult(
                success=False,
                old_solution=self.current_solution,
                new_solution=self.current_solution,
                changes=[],
                cost_delta=0,
                reoptimization_time=0,
                affected_routes=[],
                message=f"客户数据缺少必要字段: {missing_fields}",
            )

        # 添加到客户列表
        self.current_customers.append(new_customer)

        if full_reoptimize:
            # 完全重优化
            return self._full_reoptimize("新增订单触发完全重优化")
        else:
            # 使用插入启发式
            return self._insert_customer(new_customer)

    def _handle_cancel_order(
        self,
        event: DynamicEvent,
        full_reoptimize: bool,
    ) -> ReoptimizationResult:
        """
        处理取消订单事件。

        从路线中移除指定客户。
        """
        customer_id = event.data.get("customer_id")
        if customer_id is None:
            return ReoptimizationResult(
                success=False,
                old_solution=self.current_solution,
                new_solution=self.current_solution,
                changes=[],
                cost_delta=0,
                reoptimization_time=0,
                affected_routes=[],
                message="缺少客户ID",
            )

        # 从客户列表移除
        self.current_customers = [c for c in self.current_customers if c.get("id") != customer_id]

        if full_reoptimize:
            return self._full_reoptimize("取消订单触发完全重优化")
        else:
            return self._remove_customer(customer_id)

    def _handle_traffic_delay(
        self,
        event: DynamicEvent,
        full_reoptimize: bool,
    ) -> ReoptimizationResult:
        """
        处理交通延误事件。

        更新时间矩阵，可能导致路线调整。
        """
        delay_minutes = event.data.get("delay_minutes", 0)
        affected_segment = event.data.get("segment")  # (from_id, to_id)

        if not affected_segment:
            return ReoptimizationResult(
                success=False,
                old_solution=self.current_solution,
                new_solution=self.current_solution,
                changes=[],
                cost_delta=0,
                reoptimization_time=0,
                affected_routes=[],
                message="缺少延误路段信息",
            )

        # 简化处理：标记受影响的路线
        affected_routes = self._find_affected_routes(affected_segment)

        if full_reoptimize or len(affected_routes) > 2:
            return self._full_reoptimize("交通延误触发完全重优化")
        else:
            # 局部调整时间窗
            return self._adjust_for_delay(affected_routes, delay_minutes)

    def _handle_vehicle_breakdown(
        self,
        event: DynamicEvent,
        full_reoptimize: bool,
    ) -> ReoptimizationResult:
        """
        处理车辆故障事件。

        重新分配受影响路线的客户。
        """
        vehicle_id = event.data.get("vehicle_id")
        if vehicle_id is None:
            return ReoptimizationResult(
                success=False,
                old_solution=self.current_solution,
                new_solution=self.current_solution,
                changes=[],
                cost_delta=0,
                reoptimization_time=0,
                affected_routes=[],
                message="缺少车辆ID",
            )

        # 标记车辆不可用
        affected_route = self._find_route_by_vehicle(vehicle_id)

        if affected_route is None:
            return ReoptimizationResult(
                success=True,
                old_solution=self.current_solution,
                new_solution=self.current_solution,
                changes=[],
                cost_delta=0,
                reoptimization_time=0,
                affected_routes=[],
                message="车辆未在使用中",
            )

        # 需要完全重优化
        return self._full_reoptimize(f"车辆 {vehicle_id} 故障触发完全重优化")

    def _insert_customer(
        self,
        new_customer: Dict[str, Any],
    ) -> ReoptimizationResult:
        """
        使用最小成本插入启发式插入新客户。

        找到使总成本增加最少的插入位置。
        """
        routes = self.current_solution.get("routes", [])
        best_route_idx = -1
        best_insert_pos = -1
        min_cost_increase = float("inf")

        # 计算新客户的成本参数
        new_demand = new_customer.get("demand", 0)

        changes = []

        for route_idx, route in enumerate(routes):
            # 检查容量约束
            remaining_capacity = route.get("capacity", 0) - route.get("total_demand", 0)

            if remaining_capacity < new_demand:
                continue

            # 尝试各插入位置
            stops = route.get("stops", [])
            for pos in range(1, len(stops)):
                # 计算插入成本（简化：使用距离增量）
                prev_stop = stops[pos - 1]
                next_stop = stops[pos]

                # 简化距离计算
                new_lat = new_customer.get("lat", 0)
                new_lon = new_customer.get("lon", 0)
                prev_lat = prev_stop.get("lat", 0)
                prev_lon = prev_stop.get("lon", 0)
                next_lat = next_stop.get("lat", 0)
                next_lon = next_stop.get("lon", 0)

                # 增量距离
                old_dist = haversine_distance(prev_lat, prev_lon, next_lat, next_lon)
                new_dist = haversine_distance(
                    prev_lat, prev_lon, new_lat, new_lon
                ) + haversine_distance(new_lat, new_lon, next_lat, next_lon)

                cost_increase = new_dist - old_dist

                if cost_increase < min_cost_increase:
                    min_cost_increase = cost_increase
                    best_route_idx = route_idx
                    best_insert_pos = pos

        if best_route_idx < 0:
            # 无法插入现有路线，需要新增路线
            return self._full_reoptimize("无法插入新客户，触发完全重优化")

        # 执行插入
        new_solution = self._perform_insertion(best_route_idx, best_insert_pos, new_customer)

        old_cost = self.current_solution.get("cost_data", {}).get("total_cost", 0)
        new_cost = new_solution.get("cost_data", {}).get("total_cost", 0)

        changes.append(
            {
                "type": "insert",
                "route": best_route_idx,
                "position": best_insert_pos,
                "customer_id": new_customer.get("id"),
            }
        )

        return ReoptimizationResult(
            success=True,
            old_solution=self.current_solution,
            new_solution=new_solution,
            changes=changes,
            cost_delta=new_cost - old_cost,
            reoptimization_time=0,
            affected_routes=[best_route_idx],
            message=f"成功插入客户 {new_customer.get('id')} 到路线 {best_route_idx}",
        )

    def _remove_customer(
        self,
        customer_id: int,
    ) -> ReoptimizationResult:
        """
        从路线中移除客户。
        """
        routes = self.current_solution.get("routes", [])
        changes = []
        affected_routes = []

        new_routes = []

        for route_idx, route in enumerate(routes):
            new_stops = [s for s in route.get("stops", []) if s.get("customer_id") != customer_id]

            if len(new_stops) != len(route.get("stops", [])):
                # 该路线包含要移除的客户，创建新路线对象避免修改原始数据
                changes.append(
                    {
                        "type": "remove",
                        "route": route_idx,
                        "customer_id": customer_id,
                    }
                )
                affected_routes.append(route_idx)

                # 创建新路线对象，避免原地修改 current_solution
                new_route = dict(route)
                new_route["stops"] = new_stops
                new_route["total_demand"] = sum(
                    s.get("demand", 0) for s in new_stops if s.get("node", 0) > 0
                )
                new_routes.append(new_route)
            else:
                new_routes.append(route)

        if not changes:
            return ReoptimizationResult(
                success=True,
                old_solution=self.current_solution,
                new_solution=self.current_solution,
                changes=[],
                cost_delta=0,
                reoptimization_time=0,
                affected_routes=[],
                message=f"未找到客户 {customer_id}",
            )

        # 更新解
        new_solution = self.current_solution.copy()
        new_solution["routes"] = new_routes

        # 移除空路线（有效路线至少需要: 仓库 + 客户 + 仓库 = 3个站点）
        new_routes = [r for r in new_routes if len(r.get("stops", [])) >= 3]
        new_solution["routes"] = new_routes

        old_cost = self.current_solution.get("cost_data", {}).get("total_cost", 0)
        new_cost = new_solution.get("cost_data", {}).get("total_cost", 0)

        return ReoptimizationResult(
            success=True,
            old_solution=self.current_solution,
            new_solution=new_solution,
            changes=changes,
            cost_delta=new_cost - old_cost,
            reoptimization_time=0,
            affected_routes=affected_routes,
            message=f"成功移除客户 {customer_id}",
        )

    def _full_reoptimize(
        self,
        reason: str,
    ) -> ReoptimizationResult:
        """
        完全重优化。
        """
        try:
            # 将客户转换为 DataFrame
            customers_df = pd.DataFrame(self.current_customers)

            # 调用求解器
            new_solution = self.solver_func(
                customers_df,
                self.vehicle_config,
                self.params,
            )

            old_cost = self.current_solution.get("cost_data", {}).get("total_cost", 0)
            new_cost = new_solution.get("cost_data", {}).get("total_cost", 0)

            return ReoptimizationResult(
                success=True,
                old_solution=self.current_solution,
                new_solution=new_solution,
                changes=[{"type": "full_reoptimize", "reason": reason}],
                cost_delta=new_cost - old_cost,
                reoptimization_time=0,
                affected_routes=list(range(len(new_solution.get("routes", [])))),
                message=reason,
            )
        except Exception as e:
            return ReoptimizationResult(
                success=False,
                old_solution=self.current_solution,
                new_solution=self.current_solution,
                changes=[],
                cost_delta=0,
                reoptimization_time=0,
                affected_routes=[],
                message=f"重优化失败: {str(e)}",
            )

    def _find_affected_routes(
        self,
        segment: Tuple[int, int],
    ) -> List[int]:
        """
        找到包含指定路段的路线。
        """
        from_id, to_id = segment
        affected = []

        for route_idx, route in enumerate(self.current_solution.get("routes", [])):
            stops = route.get("stops", [])
            for i in range(len(stops) - 1):
                if (
                    stops[i].get("customer_id") == from_id
                    and stops[i + 1].get("customer_id") == to_id
                ):
                    affected.append(route_idx)
                    break

        return affected

    def _find_route_by_vehicle(
        self,
        vehicle_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        找到指定车辆对应的路线。
        """
        for route in self.current_solution.get("routes", []):
            if route.get("vehicle_id") == vehicle_id:
                return route
        return None

    def _adjust_for_delay(
        self,
        affected_routes: List[int],
        delay_minutes: int,
    ) -> ReoptimizationResult:
        """
        为延误调整时间窗。
        """
        # 使用浅拷贝替代 deepcopy，只复制需要的层级
        import json
        new_solution = json.loads(json.dumps(self.current_solution))
        changes = []

        for route_idx in affected_routes:
            if route_idx < len(new_solution.get("routes", [])):
                route = new_solution["routes"][route_idx]
                # 更新到达时间
                for stop in route.get("stops", []):
                    if stop.get("node", 0) > 0:  # 非仓库
                        stop["arrival_time"] = stop.get("arrival_time", 0) + delay_minutes

                changes.append(
                    {
                        "type": "delay_adjustment",
                        "route": route_idx,
                        "delay_minutes": delay_minutes,
                    }
                )

        return ReoptimizationResult(
            success=True,
            old_solution=self.current_solution,
            new_solution=new_solution,
            changes=changes,
            cost_delta=0,  # 简化计算
            reoptimization_time=0,
            affected_routes=affected_routes,
            message=f"已为 {len(affected_routes)} 条路线调整时间",
        )

    def _perform_insertion(
        self,
        route_idx: int,
        insert_pos: int,
        new_customer: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        执行客户插入操作。
        """
        # 使用 JSON 序列化替代 deepcopy，性能更好
        import json
        new_solution = json.loads(json.dumps(self.current_solution))
        route = new_solution["routes"][route_idx]

        # 先获取ID，再递增，避免跳过一个ID
        node_id = self._next_node_id
        self._next_node_id += 1

        # 验证坐标有效性
        lat = new_customer.get("lat")
        lon = new_customer.get("lon")
        if lat is None or lon is None:
            raise ValueError(f"客户 {new_customer.get('id')} 缺少坐标信息")

        new_stop = {
            "node": node_id,  # 使用唯一节点ID
            "customer_id": new_customer.get("id"),
            "customer_name": new_customer.get("name", ""),
            "lat": lat,
            "lon": lon,
            "demand": new_customer.get("demand", 0),
            "service_time_min": new_customer.get("service_time_min", 0),
            "tw_earliest": new_customer.get("tw_earliest", 0),
            "tw_latest": new_customer.get("tw_latest", 1440),
        }

        # 插入
        route["stops"].insert(insert_pos, new_stop)
        route["total_demand"] += new_customer.get("demand", 0)

        return new_solution
