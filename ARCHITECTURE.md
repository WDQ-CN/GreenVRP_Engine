# GreenVRP Engine 架构文档

## 系统概述

GreenVRP Engine 是一个考虑碳排放的车辆路径规划（VRP）求解引擎，采用分层架构设计，支持多目标优化、动态重规划、实时追踪等功能。

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         表现层 (Presentation)                    │
├─────────────────────────────────────────────────────────────────┤
│  web_app.py          │  frontend/app.py       │  FastAPI API     │
│  (标准 Web 界面)     │  (企业简约风格)        │  (RESTful)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         业务层 (Business)                        │
├─────────────────────────────────────────────────────────────────┤
│  core/                │  optimization/         │  analysis/       │
│  - solver.py         │  - multi_objective.py  │  - comparison.py │
│  - cost.py            │  - carbon_aware.py     │  - sensitivity.py│
│  - distance.py        │  - dynamic.py          │  - strategy_eval│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         数据层 (Data)                            │
├─────────────────────────────────────────────────────────────────┤
│  models/              │  data_types/          │  config/        │
│  - customer.py        │  - customer.py         │  - constants.py  │
│  - vehicle_config.py  │  - vehicle.py          │  - settings.py   │
│  - scenario.py        │  - solution.py         │  - vehicles.py   │
│  - solution.py        │  - cost.py             │                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         支撑层 (Support)                         │
├─────────────────────────────────────────────────────────────────┤
│  tracking/            │  utils/                │  exceptions/    │
│  - position_tracker   │  - geo.py              │  - errors.py    │
│  - gps_simulator      │  - time.py             │                  │
│  - eta_calculator     │  - validation.py       │                  │
│  - geofencing         │                        │                  │
└─────────────────────────────────────────────────────────────────┘
```

## 核心模块

### 1. 核心求解层 (core/)

#### solver.py
- **功能**：VRP 求解核心引擎
- **依赖**：OR-Tools 约束求解器
- **主要类**：
  - `GreenVRPSolver`：主求解器
  - `solve_with_multiple_strategies`：多策略求解
- **算法**：
  - 容量约束 (Capacity Constraints)
  - 时间窗约束 (Time Window Constraints)
  - 车辆路径约束 (Vehicle Routing Constraints)
  - 软时间窗惩罚 (Soft Time Window Penalties)

#### cost.py
- **功能**：五维成本核算
- **成本维度**：
  1. 运输成本 (Transport Cost) - 油耗 × 油价
  2. 固定成本 (Fixed Cost) - 车辆固定开销
  3. 人工成本 (Labor Cost) - 司机时薪
  4. 碳排放成本 (Carbon Cost) - 碳排放量 × 碳价
  5. 罚金成本 (Penalty Cost) - 迟到惩罚

#### distance.py
- **功能**：距离计算
- **方法**：
  - Haversine 距离（经纬度）
  - 网格距离（曼哈顿距离）

### 2. 优化层 (optimization/)

#### carbon_aware.py
- **功能**：碳感知优化
- **方法**：
  - 加权法 (Weighted Method)
  - 约束法 (Constraint Method)
  - 层次法 (Hierarchical Method)

#### multi_objective.py
- **功能**：多目标优化
- **目标**：成本、碳排放、时间、覆盖率
- **算法**：Pareto 前沿分析

#### dynamic.py
- **功能**：动态重规划
- **事件类型**：
  - 新订单 (NEW_ORDER)
  - 订单取消 (CANCEL_ORDER)
  - 交通延误 (TRAFFIC_DELAY)
  - 车辆故障 (VEHICLE_BREAKDOWN)

### 3. 分析层 (analysis/)

#### comparison.py
- **功能**：场景对比分析
- **输出**：雷达图、热力图、对比报告

#### sensitivity.py
- **功能**：敏感度分析
- **参数**：油价、碳价、时薪、时间窗

#### strategy_eval.py
- **功能**：策略效果评估
- **指标**：求解质量、稳定性、收敛速度

### 4. 追踪层 (tracking/)

#### position_tracker.py
- **功能**：实时位置追踪
- **状态**：待命、服务中、行驶中、延误

#### gps_simulator.py
- **功能**：GPS 模拟器
- **特性**：交通模拟、路径插值

#### eta_calculator.py
- **功能**：ETA 预估
- **因素**：距离、速度、交通状况

#### geofencing.py
- **功能**：电子围栏
- **事件**：进入、离开、停留

### 5. 数据模型层 (models/)

#### customer.py
- **Customer**：客户数据模型
- **字段**：id, name, lat, lon, demand, time_window

#### vehicle_config.py
- **VehicleConfig**：车辆配置模型
- **字段**：capacity, fixed_cost, fuel_consumption, speed

#### scenario.py
- **Scenario**：场景数据模型
- **字段**：id, name, description, customers, vehicles, params

#### solution.py
- **Solution**：求解结果模型
- **字段**：routes, total_distance, total_cost, status

### 6. 数据类型层 (data_types/)

定义 Pydantic 数据模型，用于 API 请求/响应验证。

### 7. 配置层 (config/)

#### constants.py
- 默认参数常量

#### settings.py
- 系统设置配置

#### vehicles.py
- 默认车型配置

### 8. 工具层 (utils/)

#### geo.py
- 地理位置工具

#### time.py
- 时间处理工具

#### validation.py
- 数据验证工具

### 9. 异常层 (exceptions/)

自定义异常类定义。

## 数据流

### 求解流程

```
输入数据 (CSV/API)
    │
    ▼
数据验证 (validation.py)
    │
    ▼
构建求解模型 (solver.py)
    │
    ▼
OR-Tools 求解
    │
    ▼
计算成本 (cost.py)
    │
    ▼
返回结果 (Solution 对象)
    │
    ▼
可视化/导出
```

### 动态重规划流程

```
检测事件
    │
    ▼
事件分类 (dynamic.py)
    │
    ▼
更新模型状态
    │
    ▼
局部重规划
    │
    ▼
更新追踪信息 (tracking/)
    │
    ▼
返回新方案
```

## 扩展点

### 1. 添加新的优化算法

在 `optimization/` 下创建新模块：

```python
# optimization/new_algorithm.py
class NewOptimizer:
    def optimize(self, customers, vehicles, params):
        # 实现优化逻辑
        pass
```

### 2. 添加新的成本维度

修改 `core/cost.py`：

```python
def calculate_custom_cost(solution, ...):
    # 实现新成本计算
    pass
```

### 3. 添加新的可视化组件

在 `frontend/components/` 下创建新组件：

```python
# frontend/components/new_component.py
def create_new_component(data):
    # 实现可视化逻辑
    pass
```

### 4. 添加新的 API 端点

在 `api/routers/` 下创建新路由：

```python
# api/routers/new_endpoint.py
@router.post("/new-endpoint")
async def new_endpoint(request: RequestSchema):
    # 实现业务逻辑
    pass
```

## 性能优化

### 1. 求解器优化
- 使用引导局部搜索 (Guided Local Search)
- 配置合理的搜索时间限制
- 多策略并行求解

### 2. 数据缓存
- 使用 `@st.cache_data` 缓存计算结果
- 缓存距离矩阵
- 缓存常用配置

### 3. 异步处理
- 异步 API 调用
- 后台任务队列
- WebSocket 实时推送

## 安全考虑

### 1. 数据验证
- 使用 Pydantic 进行输入验证
- 限制请求大小
- SQL 注入防护

### 2. 访问控制
- API 认证（预留接口）
- 速率限制
- CORS 配置

### 3. 错误处理
- 自定义异常类
- 详细的错误日志
- 用户友好的错误消息

## 部署架构

```
┌─────────────────┐
│   负载均衡器    │
└────────┬────────┘
         │
    ┌────┼────┐
    │    │    │
┌───▼──┐┌───▼──┐┌───▼──┐
│ API  ││ API  ││ API  │
│ 实例 ││ 实例 ││ 实例 │
└───┬──┘└───┬──┘└───┬──┘
    │       │       │
    └───────┼───────┘
            │
     ┌──────▼──────┐
     │ 共享数据库   │
     │  (可选)     │
     └─────────────┘
```

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| Web 框架 | FastAPI, Streamlit |
| 求解器 | OR-Tools |
| 数据处理 | Pandas, NumPy |
| 可视化 | Plotly, Folium |
| 数据验证 | Pydantic |
| 测试 | Pytest |
| 数据库 | SQLAlchemy (可选) |

## 贡献指南

1. 遵循代码规范 (PEP 8)
2. 编写单元测试
3. 更新文档
4. 提交 Pull Request

## 许可证

MIT License
