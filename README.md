# GreenVRP Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![OR-Tools](https://img.shields.io/badge/or--tools-9.7+-orange.svg)](https://developers.google.com/optimization)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**绿色车辆路径规划引擎** - 考虑碳排放的智能物流路径优化系统

## 项目简介

GreenVRP Engine 是一个专注于绿色物流的车辆路径规划（VRP）求解引擎。系统以碳排放为核心优化目标，综合考虑运输成本、时间窗约束、车辆容量等多维度因素，为企业提供可持续发展的物流决策支持。

### 核心特性

- 🌱 **碳感知优化** - 以碳排放为主要优化目标，支持碳预算约束
- 📊 **五维成本核算** - 运输、固定、人工、碳排、罚金成本全面覆盖
- 🚚 **多车型支持** - 支持 4.2m、7.6m、9.6m 等多种车型混合调度
- ⏱️ **软时间窗** - 支持迟到罚金的弹性时间窗
- 🔄 **动态需求响应** - 实时订单变更、交通延误、车辆故障处理
- 📍 **实时位置追踪** - GPS 模拟与车辆状态监控（计划中）
- 📈 **多场景分析** - 策略评估、敏感度分析、场景对比
- 🎯 **REST API** - 完整的 API 接口，支持系统集成

## 快速开始

### 环境要求

- Python 3.10+
- Windows / Linux / macOS

### 安装

```bash
# 克隆项目
git clone https://github.com/your-org/green-vrp-engine.git
cd green-vrp-engine

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-test.txt  # 安装测试依赖（可选）
```

`.venv` 目录已排除版本控制，建议为每个环境创建独立虚拟环境。

### 基本使用

```python
import pandas as pd
from core.solver import GreenVRPSolver, solve_with_multiple_strategies
from core.cost import calculate_green_cost
from config.vehicles import DEFAULT_VEHICLE_CONFIG
from config.constants import DEFAULT_PARAMS

# 加载客户数据
df = pd.read_csv('data/mock_customers.csv')

# 创建求解器
solver = GreenVRPSolver(
    customers_df=df,
    vehicle_config=DEFAULT_VEHICLE_CONFIG,
    time_penalty_per_min=10.0,
    search_time_limit=60,
)

# 求解
solution = solver.solve()

# 计算成本
cost_result = calculate_green_cost(solution, DEFAULT_VEHICLE_CONFIG, DEFAULT_PARAMS)

# 输出结果
print(f"总距离: {solution['total_distance']:.2f} km")
print(f"总成本: ¥{cost_result['total_cost']:,.2f}")
print(f"碳排放: {cost_result['carbon_emission_kg']:.2f} kg CO2")
```

## 项目结构

```
green_vrp_engine/
├── api/                    # REST API 模块
│   ├── main.py            # FastAPI 应用入口
│   ├── routers/           # API 路由
│   │   ├── solver.py      # 求解接口
│   │   ├── scenarios.py   # 场景管理
│   │   └── health.py      # 健康检查
│   ├── schemas/           # Pydantic 数据模型
│   │   ├── request.py     # 请求模型
│   │   └── response.py    # 响应模型
│   └── services/          # 业务逻辑层
│       └── solver_service.py
│
├── core/                   # 核心模块
│   ├── distance.py        # 距离计算（Haversine、网格距离）
│   ├── cost.py            # 五维成本核算
│   └── solver.py          # VRP 求解器
│
├── optimization/           # 优化模块
│   ├── multi_objective.py # 多目标优化
│   ├── carbon_aware.py    # 碳感知优化
│   └── dynamic.py         # 动态重优化
│
├── analysis/               # 分析模块
│   ├── comparison.py      # 场景对比分析
│   ├── sensitivity.py     # 敏感度分析
│   └── strategy_eval.py   # 策略效果评估
│
├── tracking/               # 追踪模块（计划中）
│
├── models/                 # 数据模型层
│   ├── customer.py        # 客户模型
│   ├── vehicle_config.py  # 车辆配置模型
│   ├── scenario.py        # 场景模型
│   ├── solution.py        # 求解结果模型
│   └── database.py        # 数据库模型
│
├── data_types/             # 数据类型定义
│   ├── customer.py        # 客户数据类型
│   ├── vehicle.py         # 车辆数据类型
│   ├── solution.py        # 求解结果类型
│   └── cost.py            # 成本数据类型
│
├── config/                 # 配置模块
│   ├── constants.py       # 常量定义
│   ├── settings.py        # 系统设置
│   └── vehicles.py        # 默认车型配置
│
├── utils/                  # 工具模块
│   ├── geo.py             # 地理位置工具
│   ├── time.py            # 时间处理工具
│   └── validation.py      # 数据验证工具
│
├── exceptions/             # 异常定义
│   └── errors.py          # 自定义异常类
│
├── tests/                  # 测试套件
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   ├── fixtures/          # 测试夹具
│   └── utils/             # 测试工具
│
├── data/                   # 数据目录
│   └── mock_customers.csv # 示例客户数据
│
├── frontend/               # 前端界面
│   ├── app.py             # 企业简约风格前端
│   ├── config.py           # 前端配置
│   └── components/        # UI 组件
│
├── start_fast.py           # 高性能启动器
├── web_app.py              # Streamlit Web 应用
├── start_enterprise_ui.py   # 企业 UI 启动器
├── start_optimized.py      # 优化版启动器
├── requirements.txt         # 运行依赖
└── requirements-test.txt    # 测试依赖
```

## 核心功能详解

### 1. 碳感知优化

支持三种碳优化方法：

```python
from optimization.carbon_aware import CarbonAwareOptimizer

optimizer = CarbonAwareOptimizer(solver_func, customers, vehicle_config, params)

# 加权法：将碳排放作为优化目标之一
result = optimizer.optimize_for_carbon(method="weighted")

# 约束法：将碳排放作为硬约束
result = optimizer.optimize_for_carbon(
    carbon_target=50,  # 目标 50kg CO2
    method="constraint"
)

# 层次法：先优化碳排放，再优化成本
result = optimizer.optimize_for_carbon(method="hierarchical")

# 计算碳效率报告
report = optimizer.calculate_carbon_efficiency(result)
print(f"总碳排放: {report.total_carbon_kg:.2f} kg CO2")
print(f"单位距离碳排放: {report.carbon_per_km:.4f} kg/km")
```

### 2. 五维成本核算

```python
from core.cost import calculate_green_cost

result = calculate_green_cost(solution, vehicle_config, params)

# 输出成本明细
print(f"运输成本: {result['transport_cost']:.2f} 元")
print(f"固定成本: {result['fixed_cost']:.2f} 元")
print(f"人工成本: {result['labor_cost']:.2f} 元")
print(f"碳排放成本: {result['carbon_cost']:.2f} 元")
print(f"罚金成本: {result['penalty_cost']:.2f} 元")
print(f"总成本: {result['total_cost']:.2f} 元")
print(f"碳排放量: {result['carbon_emission_kg']:.2f} kg CO2")
```

### 3. 动态需求响应

支持处理多种动态事件：

```python
from optimization.dynamic import DynamicReoptimizer, DynamicEvent, EventType

reoptimizer = DynamicReoptimizer(solver_func, customers, vehicle_config, params)
reoptimizer.set_current_solution(current_solution)

# 处理新订单
event = DynamicEvent(
    event_type=EventType.NEW_ORDER,
    timestamp=time.time(),
    data={"customer": new_customer}
)
result = reoptimizer.handle_event(event)

# 处理订单取消
event = DynamicEvent(
    event_type=EventType.CANCEL_ORDER,
    timestamp=time.time(),
    data={"customer_id": 5}
)
result = reoptimizer.handle_event(event)

# 处理交通延误
event = DynamicEvent(
    event_type=EventType.TRAFFIC_DELAY,
    timestamp=time.time(),
    data={"delay_minutes": 30, "segment": (1, 2)}
)
result = reoptimizer.handle_event(event)

# 处理车辆故障
event = DynamicEvent(
    event_type=EventType.VEHICLE_BREAKDOWN,
    timestamp=time.time(),
    data={"vehicle_id": 0}
)
result = reoptimizer.handle_event(event)
```

### 4. 实时位置追踪（计划中）

> `tracking/` 模块尚在开发中，计划包含：位置追踪、GPS 模拟、电子围栏、ETA 预估等功能。

### 5. 多场景对比分析（需先完成求解）

```python
from analysis.comparison import ScenarioComparison

comparison = ScenarioComparison()
result = comparison.compare_solutions(
    [solution_a, solution_b, solution_c],
    scenario_names=["方案A", "方案B", "方案C"]
)

print(f"最优方案: {result.best_scenario}")

# 生成雷达图
fig = comparison.generate_radar_chart(result)
fig.show()

# 生成柱状图
fig = comparison.generate_bar_comparison(result, metric="total_cost")

# 生成热力图
fig = comparison.generate_heatmap(result)

# 生成文本报告
report = comparison.generate_comparison_report(result)
print(report)
```

### 6. 策略效果评估

```python
from analysis.strategy_eval import StrategyEvaluator

evaluator = StrategyEvaluator(solver_func, customers, vehicle_config, params)

# 评估多种策略
result = evaluator.evaluate_strategies(
    strategies=["fast", "balanced", "thorough"],
    time_limits=[30, 60, 120],
    num_runs=3
)

print(f"推荐策略: {result.best_strategy}")
print(f"稳定性评分: {result.stability_scores}")

# 生成评估报告
report = evaluator.generate_evaluation_report(result)
```

## REST API

### 启动方式

**Windows 双击启动：**
```bash
# 双击 start_api.bat
```

**命令行启动：**
```bash
# 使用高性能启动器
python start_fast.py api
python start_fast.py api --port 8001  # 指定端口

# 直接启动
uvicorn api.main:app --reload --port 8000
```

访问 API 文档：http://localhost:8000/docs
访问 ReDoc 文档：http://localhost:8000/redoc

### 主要接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/solve` | POST | 同步求解 VRP |
| `/api/v1/solve/async` | POST | 异步求解（创建任务） |
| `/api/v1/solve/jobs/{job_id}` | GET | 查询任务状态 |
| `/api/v1/solve/jobs/{job_id}/result` | GET | 获取求解结果 |
| `/api/v1/scenarios` | GET | 获取场景列表 |
| `/api/v1/scenarios` | POST | 创建场景 |
| `/api/v1/scenarios/{id}` | GET | 获取场景详情 |
| `/api/v1/scenarios/{id}` | PUT | 更新场景 |
| `/api/v1/scenarios/{id}` | DELETE | 删除场景 |
| `/api/v1/health` | GET | 健康检查 |

### 示例请求

```bash
# 同步求解
curl -X POST "http://localhost:8000/api/v1/solve" \
  -H "Content-Type: application/json" \
  -d '{
    "customers": [
      {"id": 0, "name": "仓库", "lat": 39.9042, "lon": 116.4074, "demand": 0, "service_time_min": 0, "tw_earliest": 480, "tw_latest": 960},
      {"id": 1, "name": "客户A", "lat": 39.9142, "lon": 116.4174, "demand": 50, "service_time_min": 15, "tw_earliest": 500, "tw_latest": 600}
    ],
    "params": {
      "fuel_price": 7.5,
      "search_time_limit": 30
    }
  }'

# 异步求解
curl -X POST "http://localhost:8000/api/v1/solve/async" \
  -H "Content-Type: application/json" \
  -d '{...}'

# 查询任务状态
curl "http://localhost:8000/api/v1/jobs/{job_id}"
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行特定模块测试
pytest tests/unit/core/ -v
pytest tests/unit/optimization/ -v
pytest tests/unit/tracking/ -v
pytest tests/unit/analysis/ -v

# 生成覆盖率报告
pytest --cov=. --cov-report=html --cov-report=term

# 查看覆盖率报告
# 打开 htmlcov/index.html
```

### 测试覆盖

| 模块 | 测试文件 | 测试用例数 |
|------|----------|------------|
| core | test_distance.py, test_cost.py, test_solver.py | ~120 |
| optimization | test_multi_objective.py, test_carbon_aware.py, test_dynamic.py | ~150 |
| analysis | test_comparison.py, test_sensitivity.py, test_strategy_eval.py | ~100 |
| tracking | （计划中） | — |
| api | test_routers.py, test_schemas.py | ~50 |

总计：约 248 测试函数（51%+ 行覆盖率）

## 配置参数

### 全局参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| `fuel_price` | 7.5<br/> | 油价（元/升） |
| `hourly_wage` | 50 | 时薪（元/小时） |
| `carbon_price` | 0.08 | 碳价（元/kg CO2） |
| `late_penalty_per_min` | 10 | 迟到罚金（元/分钟） |

### 车型配置

| 车型 | 容量(kg) | 固定成本(元) | 油耗(L/100km) | 时速(km/h) |
|------|----------|--------------|---------------|------------|
| 4.2m | 800 | 200 | 12 | 40 |
| 7.6m | 1500 | 350 | 18 | 35 |
| 9.6m | 2500 | 500 | 25 | 30 |

## 碳排放计算

系统使用柴油碳排放因子：**2.63 kg CO2 / 升**

```
碳排放量 (kg CO2) = 油耗 (升) × 2.63
                 = 行驶距离 (km) × 油耗系数 (L/100km) / 100 × 2.63

碳排放成本 (元) = 碳排放量 (kg CO2) × 碳价 (元/kg)
```

## 算法特点

### 求解器

- 基于 OR-Tools 约束求解器
- 支持引导局部搜索（Guided Local Search）
- 可配置求解时间限制
- 支持多车型异构车队

### 优化策略

| 策略 | 时间限制 | 适用场景 |
|------|----------|----------|
| fast | 30秒 | 快速响应，实时决策 |
| balanced | 60秒 | 平衡质量与效率 |
| thorough | 120秒 | 追求最优解 |

### 多目标优化

支持三种多目标优化方法：

1. **加权法** - 将多目标加权求和为单目标
2. **ε-约束法** - 将部分目标转化为约束条件
3. **层次法** - 按优先级依次优化各目标

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| Web 框架 | FastAPI |
| 求解器 | OR-Tools |
| 数据处理 | Pandas, NumPy |
| 可视化 | Plotly, Folium |
| 界面 | Streamlit |
| 测试 | Pytest |

## Web 可视化应用

### 快速启动

**方式一：双击启动（Windows）**
```bash
# 双击 start_web.bat 启动标准 Web 界面
# 双击 run_enterprise_ui.bat 启动企业简约风格界面
```

**方式二：命令行启动**
```bash
# 使用高性能启动器（推荐）
python start_fast.py              # 交互式选择
python start_fast.py web          # 启动标准 Web 界面
python start_fast.py api          # 启动 API 服务

# 使用企业简约风格前端
python start_enterprise_ui.py

# 使用标准启动器
python start.py                    web  # 交互式选择
```

**方式三：直接运行**
```bash
# Streamlit Web 界面（标准版本）
streamlit run web_app.py

# Streamlit Web 界面（企业简约风格）
streamlit run frontend/app.py
```

### Web 界面功能

**标准版本 (web_app.py)：**
- 📍 **交互式路线地图** - Folium 地图可视化，支持缩放、点击查看详情
- 📊 **五维成本分析** - 饼图展示成本构成，关键指标卡片
- 📋 **车辆使用情况** - 车型利用率统计，容量分析
- ⚙️ **参数配置面板** - 经济参数、求解器设置、车型配置
- 📁 **数据导入导出** - 支持 CSV 格式客户数据导入

**企业简约风格 (frontend/app.py)：**
- 📊 **仪表板** - 实时状态监控、关键指标展示、求解进度跟踪
- 🗺️ **路线规划** - 交互式地图、路线统计、车辆轨迹展示
- 💰 **成本分析** - 五维成本核算、成本结构、碳排放分析、效率指标
- 📈 **对比分析** - 多方案对比、性能指标对比、碳排放对比

访问地址：http://localhost:8501

## 开发指南

### 代码规范

- 遵循 PEP 8 编码规范
- 使用类型注解
- 编写中文注释和文档字符串
- 单元测试覆盖核心功能

### 提交代码

```bash
# 运行测试
pytest tests/

# 检查代码风格
flake8 .

# 提交
git add .
git commit -m "feat: 添加新功能"
git push
```

## 路线图

- [x] 核心 VRP 求解器
- [x] 五维成本核算
- [x] 碳感知优化
- [x] 动态需求响应
- [x] REST API 接口
- [x] 实时位置追踪
- [ ] 机器学习需求预测
- [ ] 多仓库支持
- [ ] 电动车辆充电规划

## 相关文档

- [README.md](README.md) - 项目主文档
- [QUICKSTART.md](QUICKSTART.md) - 快速开始指南
- [ARCHITECTURE.md](ARCHITECTURE.md) - 架构文档
- [DEVELOPER.md](DEVELOPER.md) - 开发者指南
- [CHANGELOG.md](CHANGELOG.md) - 更新日志

## 许可证

MIT License

## 致谢

- [OR-Tools](https://developers.google.com/optimization) - Google 优化工具包
- [FastAPI](https://fastapi.tiangolo.com/) - 现代高性能 Web 框架
- [Streamlit](https://streamlit.io/) - 交互式 Web 应用框架
- [Folium](https://python-visualization.github.io/folium/) - 地图可视化库

## 联系方式

- 项目主页: https://github.com/your-org/green-vrp-engine
- 问题反馈: https://github.com/your-org/green-vrp-engine/issues

---

**让物流更绿色，让配送更高效** 🌍
