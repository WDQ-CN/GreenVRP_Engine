# GreenVRP Engine 架构文档

## 系统概述

GreenVRP Engine 是一个考虑碳排放的车辆路径规划（VRP）求解引擎，采用分层架构设计，支持多目标优化、动态重规划、实时追踪、REST API 等功能。

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
│  - solver.py          │  - multi_objective.py  │  - comparison.py │
│  - cost.py            │  - carbon_aware.py     │  - sensitivity.py│
│  - distance.py        │  - dynamic.py          │  - strategy_eval │
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
│  - solution.py        │  - cost.py             │  - security.py   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API 层 (API Service)                         │
├─────────────────────────────────────────────────────────────────┤
│  api/routers/         │  api/services/         │  api/security/  │
│  - solver.py          │  - solver_service.py   │  - auth.py       │
│  - auth.py            │  - redis_job_manager   │  - rate_limit.py │
│  - tracking.py        │                        │                  │
│  - health.py          │                        │                  │
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
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       部署层 (Deployment)                        │
├─────────────────────────────────────────────────────────────────┤
│  Dockerfile           │  deploy/               │  .github/       │
│  docker-compose.yml   │  - nginx.conf          │  workflows/     │
│                       │  - Caddyfile           │  - ci.yml       │
│                       │                        │  - dependabot   │
└─────────────────────────────────────────────────────────────────┘
```

## 核心模块

### 1. 核心求解层 (core/)

#### solver.py
- **功能**：VRP 求解核心引擎
- **依赖**：OR-Tools 约束求解器
- **主要类**：
  - `GreenVRPSolver`：主求解器，封装 OR-Tools RoutingModel
  - `solve_with_multiple_strategies`：多策略串行求解
  - `solve_with_multiple_strategies_parallel`：多策略并行求解（ProcessPoolExecutor）
- **算法**：
  - 容量约束 (Capacity Constraints)
  - 时间窗约束 (Time Window Constraints)
  - 车辆路径约束 (Vehicle Routing Constraints)
  - 软时间窗惩罚 (Soft Time Window Penalties)
  - 自适应搜索参数（根据问题规模动态调整）

#### cost.py
- **功能**：五维成本核算
- **成本维度**：
  1. 运输成本 (Transport Cost) - 油耗 × 油价
  2. 固定成本 (Fixed Cost) - 车辆固定开销
  3. 人工成本 (Labor Cost) - 司机时薪
  4. 碳排放成本 (Carbon Cost) - 碳排放量 × 碳价
  5. 罚金成本 (Penalty Cost) - 迟到惩罚
- **性能优化**：等待时间计算向量化、车型参数 LRU 缓存

#### distance.py
- **功能**：距离/时间矩阵计算
- **方法**：
  - Haversine 距离（经纬度）
  - 网格距离（曼哈顿距离）
- **缓存**：`DistanceMatrixCache` 多级缓存，防止重复计算

### 2. 优化层 (optimization/)

#### carbon_aware.py
- **功能**：碳感知优化
- **方法**：
  - 加权法 (Weighted Method) — 将碳排加入目标函数加权
  - 约束法 (Constraint Method) — 碳排上限作为硬约束
  - 层次法 (Hierarchical Method) — 优先优化成本，次优优化碳排

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
- **输出**：龙卷风图、折线图、热力图、分析报告

#### strategy_eval.py
- **功能**：策略效果评估
- **指标**：求解质量、稳定性、收敛速度

### 4. API 服务层 (api/)

#### api/routers/
- **solver.py**：VRP 求解端点（同步/异步）
- **auth.py**：认证相关端点（登录、刷新令牌）
- **tracking.py**：位置追踪端点
- **health.py**：健康检查端点

#### api/services/
- **solver_service.py**：求解业务逻辑（单次/批量/异步）
- **redis_job_manager.py**：基于 Redis 的异步任务管理器

#### api/security/
- **auth.py**：API Key + JWT 双重认证机制
- **rate_limit.py**：基于 slowapi 的速率限制（IP + API Key 双重键值）

### 5. 追踪层 (tracking/)

#### position_tracker.py
- **功能**：实时位置追踪
- **状态**：待命、服务中、行驶中、延误

#### gps_simulator.py
- **功能**：GPS 模拟器
- **特性**：交通模拟、路径插值、实时位置更新

#### eta_calculator.py
- **功能**：ETA 预估
- **因素**：距离、速度、交通状况、历史数据

#### geofencing.py
- **功能**：电子围栏
- **事件**：进入、离开、停留、超时告警

### 6. 数据模型层 (models/)

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

### 7. 数据类型层 (data_types/)

定义 Pydantic TypedDict，用于类型安全的数据传递：
- `SolutionDict`、`RouteDict`、`StopDict`、`CostDict`

### 8. 配置层 (config/)

#### constants.py
- 默认参数常量（碳排放系数、默认成本参数等）

#### settings.py
- 系统设置配置（环境变量加载）

#### vehicles.py
- 默认车型配置（油耗、速度、容量等）

#### security.py
- 安全配置（API Key、JWT、CORS、速率限制、SSRF 防护）
- 生产环境强制 API Key 和 JWT 密钥配置

### 9. 工具层 (utils/)

#### geo.py
- 地理位置工具（坐标转换、距离计算、区域判断）

#### time.py
- 时间处理工具（时间窗解析、时间格式化）

#### validation.py
- 数据验证工具（输入校验、格式检查）

### 10. 异常层 (exceptions/)

自定义异常类体系，统一错误处理：
- `GreenVRPError`（基类）
- `ValidationError`、`SolverError`、`ConfigError`、`AuthError` 等

### 11. 部署层 (deploy/)

- **Dockerfile** + **docker-compose.yml**：容器化部署
- **deploy/nginx.conf**：Nginx 反向代理配置
- **deploy/Caddyfile**：Caddy 自动 HTTPS 配置
- **.github/workflows/ci.yml**：CI/CD 流水线

## 测试结构

```
tests/
├── unit/                    # 单元测试
│   ├── core/               # solver, cost, distance
│   ├── api/                # auth, rate_limit, solver_service
│   ├── models/             # customer, vehicle_config, scenario, solution
│   ├── config/             # settings, security
│   ├── analysis/           # sensitivity, strategy_eval
│   ├── optimization/       # carbon_aware, dynamic, multi_objective
│   ├── data_types/         # cost, customer, solution, vehicle
│   └── tracking/           # position_tracker, gps_simulator, etc.
├── integration/            # 集成测试
│   ├── test_solver_integration.py
│   └── test_api_integration.py
└── conftest.py             # 全局测试夹具
```

## 数据流

### 求解流程

```
输入数据 (CSV/API JSON)
    │
    ▼
API 认证 (auth.py) — API Key / JWT Bearer Token
    │
    ▼
速率限制 (rate_limit.py) — 基于 IP + API Key 的双重限流
    │
    ▼
数据验证 (Pydantic validation)
    │
    ▼
构建求解模型 (solver.py — _setup_solver)
    │
    ▼
OR-Tools 求解 (Guided Local Search / Tabu Search / SA)
    │
    ▼
计算成本 (cost.py — calculate_green_cost)
    │
    ▼
返回结果 (Solution Dict / CostDict)
    │
    ▼
可视化/导出 (Plotly / Folium / JSON)
```

### 动态重规划流程

```
检测事件 (GPS / API 回调)
    │
    ▼
事件分类 (dynamic.py — classify_event)
    │
    ▼
更新模型状态 (update_state)
    │
    ▼
局部重规划 (dynamic.py — re_optimize)
    │
    ▼
更新追踪信息 (tracking/ — position_tracker)
    │
    ▼
返回新方案 + WebSocket 推送
```

### 异步求解流程

```
客户端发起求解请求
    │
    ▼
RedisJobManager.create_job() → 返回 job_id
    │
    ▼
后台 worker 执行求解 (solver_service)
    │
    ▼
状态轮询: GET /api/v1/solver/jobs/{job_id}
    │
    ▼
求解完成 → 返回结果 / 回调通知
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
- 配置合理的搜索时间限制（自适应策略：小规模精确、大规模启发式）
- 多策略并行求解（ProcessPoolExecutor 多进程）
- 回退机制：并行失败自动降级为串行

### 2. 数据缓存
- **DistanceMatrixCache**：距离矩阵多级缓存（LRU + MD5 哈希）
- **CallbackCache**：OR-Tools 回调数据缓存
- **SolverInstancePool**：求解器实例池（避免重复初始化）
- `@st.cache_data`：Streamlit 前端缓存
- 车型参数 LRU 缓存（`core/cost.py`）

### 3. 数值计算优化
- NumPy 向量化运算（等待时间计算等）
- SciPy 可选加速（距离矩阵计算）
- Pandas 预提取列数组（避免 `.iloc` 循环）

### 4. 异步处理
- 异步 API 调用（FastAPI async endpoints）
- Redis 后台任务队列（异步求解作业）
- WebSocket 实时推送（状态更新、追踪数据）

## 安全考虑

### 1. 认证与授权
- **API Key**：请求头 `X-API-Key`，缓存校验，生产环境强制配置
- **JWT**：Bearer Token，含过期时间，生产环境禁止默认密钥
- **速率限制**：基于 IP + API Key 的双重限流策略

### 2. 数据验证
- Pydantic 输入验证（请求体、查询参数）
- 请求大小限制
- SQL 注入防护（参数化查询）

### 3. SSRF 防护
- DNS 解析 + IP 白名单双重校验
- CIDR 黑名单（阻止内网地址）
- DDoS 防护（DNS 重绑定攻击防护）

### 4. 安全响应头
- X-Content-Type-Options, X-Frame-Options, CSP
- Strict-Transport-Security (HSTS)

### 5. 日志脱敏
- SensitiveDataFilter 自动过滤 API Key、Token、密码
- JSON 格式化输出，支持环境变量开关

### 6. 依赖安全
- CI 中 pip-audit 依赖漏洞扫描
- Bandit SAST 静态安全分析
- Dependabot 自动依赖更新

## 部署架构

```
┌─────────────────┐
│   负载均衡器    │
│  (Nginx/Caddy)  │
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
     │  Redis      │
     │  (任务队列)  │
     └─────────────┘
            │
     ┌──────▼──────┐
     │  数据库     │
     │  (可选)     │
     └─────────────┘
```

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| Web 框架 | FastAPI, Streamlit |
| 求解器 | OR-Tools |
| 数据处理 | Pandas, NumPy, SciPy（可选） |
| 可视化 | Plotly, Folium |
| 数据验证 | Pydantic v2 + TypedDict |
| 认证 | OAuth2 + JWT (python-jose) + API Key |
| 速率限制 | slowapi |
| 异步任务 | Redis (redis-py) |
| HTTP 客户端 | httpx（回调功能） |
| 测试 | Pytest（481 测试） |
| 数据库 | SQLAlchemy 2.0 (SQLite/PostgreSQL，可选) |
| CI/CD | GitHub Actions |
| 容器化 | Docker |
| 反向代理 | Nginx / Caddy (自动 HTTPS) |
| 代码工具 | Black, isort, flake8, mypy, pre-commit |
| 安全扫描 | Bandit (SAST), pip-audit (依赖), Dependabot |

## 贡献指南

1. 遵循代码规范 (PEP 8 + Black 格式化)
2. 所有代码须通过类型检查 (mypy)
3. 编写单元测试，确保测试覆盖
4. 更新文档（ARCHITECTURE.md / docstring）
5. 提交 Pull Request 前运行完整测试套件

## 许可证

MIT License
