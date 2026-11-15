# GreenVRP Engine

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104%2B-green.svg)](https://fastapi.tiangolo.com/)
[![OR-Tools](https://img.shields.io/badge/or--tools-9.7%2B-orange.svg)](https://developers.google.com/optimization)
[![React](https://img.shields.io/badge/react-19%2B-149eca.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**绿色车辆路径规划引擎** — 把碳排放放进目标函数的异构车队 VRPTW 求解系统。

## 项目简介

GreenVRP Engine 面向城市配送场景，在容量、软时间窗、异构车队与工作时长约束下，同时优化运输、人工、固定、违约与碳排五维成本。引擎以 OR-Tools 为首解与精确子问题求解器，叠加载重感知二次优化、多种子 ALNS、路线池重组与 CP-SAT 配对精修，并提供 FastAPI、React Web 控制台与 Streamlit 界面。

## 核心特性

- **五维成本目标**：运输（含载重相关油耗）、人工（行驶 + 等待 + 服务）、车辆固定、迟到罚金、碳排成本统一进入目标函数。
- **载重相关油耗**：额定油耗作为 50% 载重基准，空载 0.75×、满载 1.25×，按逐段剩余载重线性插值。
- **时变速度**：早高峰 0.65×、晚高峰 0.70×，并自动优化发车时刻以避开高峰、减少等待。
- **车队数量是上限**：`count` 表示可用车辆数，不要求全部使用；空路线不计入 `vehicles_used`，固定成本只对实际发车车辆计费。
- **异构与自定义车型**：默认 4.2m / 7.6m / 9.6m，可新增任意车型并自定义载重、固定成本、油耗与速度。
- **多种子 ALNS**：7 类破坏算子 + 3 类修复算子、自适应权重、SA/LAHC 接受准则、扰动与整路线消除。
- **精确子问题增强**：路线池 CP-SAT 集合划分、逐对路线 CP-SAT 重排、2-opt* / VND / 段搬迁后处理。
- **可复现基准**：100 节点固定种子基准，支持车队配置、ALNS 参数与流水线阶段对比。
- **双前端**：React + Vite 控制台（`web/`）与 Streamlit 界面（`web_app.py` / `frontend/app.py`）。

## 求解流水线

```
客户与车型配置
      │
      ▼
① 多策略 OR-Tools 首解（5 组策略并行，软时间窗 + 容量 + 固定成本 + 碳成本）
      │
      ▼
② 双路径首版解选择（优化前成本最优 + 短 ALNS 探针最优）
      │
      ▼
③ 载重感知二次求解（按上一轮逐车实际载重率重建弧成本）
      │
      ▼
④ 车队缩减候选（仅当当前解用满全部可用车辆时尝试减少一辆）
      │
      ▼
⑤ 多种子 ALNS（默认 16 组种子 × 固定迭代预算，含早晚高峰发车变体）
      │
      ▼
⑥ 跨种子路线池重组（CP-SAT 集合划分，保证客户覆盖与车队上限）
      │
      ▼
⑦ 2-opt* / VND / 段搬迁 / 最终重强化
      │
      ▼
⑧ CP-SAT 逐对路线精确重排（容量、时间窗、18:00 返回、白天速度）
      │
      ▼
⑨ 逐路线发车时刻优化，按真实五维成本保留最优解
```

### ALNS 算子

- 破坏：随机、最差、相关性、整路线、小路线优先、连续段、相邻路线对。
- 修复：贪心、regret-2、regret-3。
- 接受：模拟退火（默认）或 LAHC；权重按得分自适应更新，并设下限防止算子饥饿。
- 收尾：整路线消除、路线内精修与发车时刻优化。

## 快速开始

### 环境要求

- Python 3.11 / 3.12（CI 使用 3.11、3.12）
- Node.js 20+（仅 Web 控制台需要）
- Windows / Linux / macOS

### 安装

```bash
git clone https://github.com/WDQ-CN/GreenVRP_Engine.git
cd GreenVRP_Engine

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

pip install -r requirements.txt
pip install -r requirements-test.txt   # 可选：测试依赖
```

### 基本求解

```python
import pandas as pd
from core.solver import GreenVRPSolver
from core.cost import calculate_green_cost
from config.constants import DEFAULT_PARAMS
from config.vehicles import DEFAULT_VEHICLE_CONFIG

df = pd.read_csv("data/mock_customers.csv")

solver = GreenVRPSolver(
    customers_df=df,
    vehicle_config=DEFAULT_VEHICLE_CONFIG,
    time_penalty_per_min=10.0,
    search_time_limit=60,
    fuel_price=DEFAULT_PARAMS["fuel_price"],
    carbon_price=DEFAULT_PARAMS["carbon_price"],
)
solution = solver.solve()
cost = calculate_green_cost(solution, DEFAULT_VEHICLE_CONFIG, DEFAULT_PARAMS)

print(f"总距离: {solution['total_distance']:.2f} km")
print(f"总成本: ¥{cost['total_cost']:,.2f}")
print(f"碳排放: {cost['carbon_emission_kg']:.2f} kg CO2")
```

### 完整流水线（推荐）

```python
from core.solver import solve_with_multiple_strategies_parallel
from config.constants import DEFAULT_PARAMS
from config.vehicles import DEFAULT_VEHICLE_CONFIG

solution = solve_with_multiple_strategies_parallel(
    customers_df=df,
    vehicle_config=DEFAULT_VEHICLE_CONFIG,
    time_penalty_per_min=10.0,
    time_limit=45,
    cost_params=DEFAULT_PARAMS,
)
```

## 车队与成本模型

### 车队配置

```python
vehicle_config = {
    "4.2m": {
        "capacity": 800,
        "fixed_cost": 200,
        "fuel_per_100km": 12,   # 50% 载重基准
        "speed_kmh": 40,
        "count": 5,             # 可用上限，不是必须使用数量
        "color": "#1f77b4",
    },
    "6.8m": {                   # 自定义车型
        "capacity": 1200,
        "fixed_cost": 320,
        "fuel_per_100km": 15,
        "speed_kmh": 36,
        "count": 2,
        "color": "#0f766e",
    },
}
```

可选字段 `fuel_empty_per_100km` / `fuel_full_per_100km` 用于显式指定空载/满载油耗；留空时分别取 `0.75×` / `1.25×fuel_per_100km`。

### 载重相关油耗

```text
fuel_empty = 0.75 × fuel_per_100km
fuel_full  = 1.25 × fuel_per_100km
fuel_per_100km(load_ratio) = fuel_empty + (fuel_full - fuel_empty) × load_ratio
```

### 时变速度

| 时段 | 速度系数 |
|------|----------|
| 00:00–07:00 | 1.15 |
| 07:00–09:00 | 0.65 |
| 09:00–17:00 | 1.00 |
| 17:00–19:00 | 0.70 |
| 19:00 以后 | 1.10 |

首轮 OR-Tools 使用工作日平均速度系数；ALNS 与最终成本按逐段时变速度重算，并优化每条路线的发车时刻。

### 五维成本

```text
运输成本 = Σ 逐段燃油（升） × 油价
人工成本 = (行驶 + 等待 + 服务分钟) / 60 × 时薪
固定成本 = Σ 实际发车车辆的 fixed_cost
违约成本 = 迟到分钟 × 每分钟罚金
碳排成本 = Σ 燃油（升） × 2.63 × 碳价
总成本   = 运输 + 人工 + 固定 + 违约 + 碳排
```

其中柴油碳排放因子为 **2.63 kg CO₂ / 升**。

## REST API

### 启动

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
# 或
python start_fast.py api
```

API 文档：http://localhost:8000/docs · ReDoc：http://localhost:8000/redoc

开发环境默认 API Key：`green-vrp-default-key-2024`（生产环境必须通过 `API_KEYS` 环境变量覆盖）。

### 主要接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/solve` | POST | 同步求解 |
| `/api/v1/solve/async` | POST | 异步求解 |
| `/api/v1/solve/jobs/{job_id}` | GET | 查询任务状态 |
| `/api/v1/solve/jobs/{job_id}/result` | GET | 获取任务结果 |
| `/api/v1/scenarios` | GET/POST | 场景列表 / 创建 |
| `/api/v1/scenarios/{id}` | GET/PUT/DELETE | 场景详情 / 更新 / 删除 |
| `/api/v1/health` | GET | 健康检查 |

### 示例请求

```bash
curl -X POST "http://localhost:8000/api/v1/solve" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: green-vrp-default-key-2024" \
  -d '{
    "customers": [
      {"id": 0, "name": "仓库", "lat": 39.9042, "lon": 116.4074, "demand": 0, "service_time_min": 0, "tw_earliest": 480, "tw_latest": 960},
      {"id": 1, "name": "客户A", "lat": 39.9142, "lon": 116.4174, "demand": 50, "service_time_min": 15, "tw_earliest": 500, "tw_latest": 600}
    ],
    "vehicle_config": {
      "4.2m": {"capacity": 800, "fixed_cost": 200, "fuel_per_100km": 12, "speed_kmh": 40, "count": 5, "color": "#1f77b4"}
    },
    "params": {
      "fuel_price": 7.5,
      "hourly_wage": 50,
      "carbon_price": 0.08,
      "late_penalty_per_min": 10,
      "search_time_limit": 45
    }
  }'
```

## Web 控制台

### React 控制台（`web/`）

```bash
cd web
npm install
npm run dev     # http://localhost:3000
npm run build   # 生产构建
npm run lint    # oxlint
```

功能：

- 碳价、油价、时薪、迟到罚金与求解预算调节。
- 车辆数量直接输入；载重、发车成本、油耗、速度可编辑。
- 新增 / 删除自定义车型，车队总数上限 15 辆。
- 本地演示与 FastAPI 真实引擎双模式，路线地图、五维成本与逐站清单联动。
- 方案 JSON 导出与 API 连接测试。

详见 [web/README.md](web/README.md)。

### Streamlit 界面

```bash
streamlit run web_app.py          # 标准版
streamlit run frontend/app.py     # 企业简约版
```

访问 http://localhost:8501。支持交互地图、成本分析、车辆利用率与参数配置。

## 测试与基准

### 测试

```bash
# 核心算法与数据模型（本地已验证 255 个用例通过）
pytest tests/unit/core tests/unit/models tests/unit/optimization tests/unit/utils -q

# 全量测试（CI 安装完整依赖后执行）
pytest tests/ -q --tb=short --timeout=60
```

前端校验：

```bash
npm --prefix web run build
npm --prefix web run lint
```

### 100 节点可复现基准

```bash
# 完整流水线（默认 5×4.2m + 2×7.6m 上限）
python analysis/benchmark_algorithm.py --mode full --time-limit 30

# 15 辆真实 UI 配置（5×4.2m + 5×7.6m + 5×9.6m 上限）
python analysis/benchmark_algorithm.py --mode full --fleet web15 --time-limit 30

# 先生成 stage1 缓存（fleet_cap_experiment / iteration_experiment 复用）
python analysis/benchmark_algorithm.py --mode stage1 --fleet fifteen --stage1-time 30

# 对比 ALNS 参数或车队配置
python analysis/fleet_cap_experiment.py --iterations 2000 --seeds 42,47,49,60 --workers 8
python analysis/iteration_experiment.py --iterations 2000,4000,6000 --workers 8
```

示例结果（100 客户、seed 42、`time_limit=30`）：

| 可用车队上限 | 实际使用 | 总成本 | 距离 |
|---|---:|---:|---:|
| 15 辆（10×4.2m + 5×7.6m） | 6×4.2m | 3406.90 | 342.3 km |
| 15 辆真实 UI（5/5/5） | 5×4.2m + 1×7.6m | 3577.75 | 336.3 km |
| 7 辆纯 4.2m | 6×4.2m | 3379.94 | 324.1 km |

结果受随机种子与车队配置影响，约 ±1% 波动；以实际运行输出为准。

## 项目结构

```text
GreenVRP_Engine/
├── api/                     # FastAPI 应用、路由、请求/响应模型
├── core/
│   ├── solver.py            # OR-Tools 求解、双路径精修、ALNS 编排、CP-SAT 配对
│   ├── cost.py              # 五维成本、载重油耗、时变速度
│   └── distance.py          # 距离与时间矩阵
├── optimization/
│   ├── alns.py              # 自适应大邻域搜索
│   ├── recombine.py         # 路线池 CP-SAT 集合划分
│   ├── pair_cpsat.py        # 两车 CP-SAT 精确重排
│   └── route_optimize.py    # 2-opt、Or-opt、跨路线 VND
├── utils/
│   └── time_profile.py      # 时段速度剖线与高峰发车
├── config/                  # 常量、默认车型、安全配置
├── analysis/
│   └── benchmark_algorithm.py  # 可复现 100 节点基准
├── web/                     # React + Vite 控制台
├── frontend/                # Streamlit 企业版界面
├── web_app.py               # Streamlit 标准界面
├── tests/                   # 单元 / 集成 / 基准测试
├── 文献/                    # 绿色 VRP 文献清单（PDF 不入库）
├── requirements.txt
└── requirements-test.txt
```

## 配置参数

### 全局参数（`config/constants.py`）

| 参数 | 默认值 | 描述 |
|------|--------|------|
| `fuel_price` | 7.5 | 柴油价格（元/升） |
| `hourly_wage` | 50 | 人工时薪（元/小时） |
| `carbon_price` | 0.08 | 碳价（元/kg CO₂） |
| `late_penalty_per_min` | 10 | 迟到罚金（元/分钟） |

### 默认车型（`config/vehicles.py`）

| 车型 | 载重(件) | 固定成本(元) | 油耗(L/100km) | 速度(km/h) | 默认可用数 |
|------|----------|--------------|---------------|------------|------------|
| 4.2m | 800 | 200 | 12 | 40 | 3 |
| 7.6m | 1500 | 350 | 18 | 35 | 2 |
| 9.6m | 2500 | 500 | 25 | 30 | 2 |

Web 控制台默认展示 5 / 3 / 2 辆，可直接编辑；`count` 始终是可用上限。

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.11+ / TypeScript |
| 求解器 | OR-Tools Routing + CP-SAT |
| API | FastAPI + Pydantic |
| 数据处理 | Pandas / NumPy |
| Web 控制台 | React 19 + Vite + Tailwind CSS |
| Streamlit 界面 | Streamlit + Plotly + Folium |
| 测试 | Pytest / oxlint / tsc |

## 路线图

- [x] 核心 VRPTW 求解与五维成本
- [x] 载重相关油耗与时变速度
- [x] 多种子 ALNS、路线池重组、CP-SAT 配对精修
- [x] 车队数量上限语义与自定义车型
- [x] React Web 控制台与可复现基准
- [x] REST API 与场景管理
- [ ] 实时位置追踪
- [ ] 多仓库支持
- [ ] 电动车辆充电规划
- [ ] 机器学习需求预测

## 相关文档

- [QUICKSTART.md](QUICKSTART.md) — 快速开始
- [ARCHITECTURE.md](ARCHITECTURE.md) — 架构说明
- [DEVELOPER.md](DEVELOPER.md) — 开发者指南
- [SECURITY.md](SECURITY.md) — 安全与密钥配置
- [CHANGELOG.md](CHANGELOG.md) — 更新日志
- [web/README.md](web/README.md) — Web 控制台
- [文献/文献清单.md](文献/文献清单.md) — 绿色 VRP 文献清单
- [文献/文献清单.csv](文献/文献清单.csv) — 文献表格

## 许可证

MIT License

## 致谢

- [OR-Tools](https://developers.google.com/optimization)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Streamlit](https://streamlit.io/)
- [Plotly](https://plotly.com/python/)
- [Folium](https://python-visualization.github.io/folium/)

## 联系方式

- 仓库：https://github.com/WDQ-CN/GreenVRP_Engine
- 问题反馈：https://github.com/WDQ-CN/GreenVRP_Engine/issues

---

**让物流更绿色，让配送更高效。**
