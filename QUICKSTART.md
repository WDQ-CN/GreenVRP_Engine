# GreenVRP Engine 快速使用指南

## 一、环境准备

### 1. 安装依赖

```bash
# 激活虚拟环境（如果使用虚拟环境）
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 验证安装

```bash
python -c "from core.solver import GreenVRPSolver; print('安装成功!')"
```

---

## 二、启动方式

### 方式一：Web 界面（推荐新手使用）

**高性能启动器（推荐）：**
```bash
python start_fast.py web
```

**Windows 双击启动：**
- 双击 `start_web.bat` - 标准界面
- 双击 `run_enterprise_ui.bat` - 企业简约风格界面

**命令行启动：**
```bash
# 标准界面
python start.py web

# 企业简约风格界面
python start_enterprise_ui.py

# 直接运行 Streamlit
streamlit run web_app.py
streamlit run frontend/app.py
```

访问地址：http://localhost:8501

### 方式二：API 服务

**高性能启动器（推荐）：**
```bash
python start_fast.py api
python start_fast.py api --port 8001  # 指定端口
```

**Windows 双击启动：**
- 双击 `start_api.bat`

**命令行启动：**
```bash
python start.py api
python start.py api --port 8001

# 直接运行
uvicorn api.main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs
ReDoc 文档：http://localhost:8000/redoc

### 方式三：命令行求解

```bash
python start_fast.py solve -i data/mock_customers.csv -o result.json
python start_fast.py solve -i data.csv -t 60 -o result.json
```

### 方式四：交互式选择

```bash
python start_fast.py
# 根据提示选择启动模式
```

---

## 三、Web 界面使用流程

### 步骤 1：加载数据

- 点击左侧边栏的"📂 加载示例数据"按钮
- 或上传 CSV 格式的客户数据文件

CSV 格式要求：
```csv
id,name,lat,lon,demand,service_time_min,tw_earliest,tw_latest
0,仓库,39.9042,116.4074,0,0,480,960
1,客户A,39.9123,116.3456,45,15,500,600
```

字段说明：
- `id`：客户唯一标识（仓库必须为 0）
- `name`：客户名称
- `lat`、`lon`：经纬度坐标
- `demand`：需求量
- `service_time_min`：服务时长（分钟）
- `tw_earliest`、`tw_latest`：时间窗（分钟，从 0:00 开始）

### 步骤 2：配置参数

在左侧边栏配置：

**经济参数：**
- 油价：7.5 元/升
- 时薪：50 元/小时
- 碳价：0.08 元/kg
- 迟到罚金：10 元/分钟

**求解器设置：**
- 求解时间限制：10-300 秒
- 多策略求解：开启

**车型配置：**
- 4.2m 小型车：容量 800 件，数量 3
- 7.6m 中型车：容量 1500 件，数量 2
- 9.6m 大型车：容量 2500 件，数量 2

### 步骤 3：开始求解

点击"🚀 开始求解"按钮，等待求解完成。

### 步骤 4：查看结果

**地图可视化：**
- 查看路线分布
- 点击站点查看详情
- 识别迟到站点（橙色标记）

**成本分析：**
- 总成本构成饼图
- 五维成本明细
- 效率指标

**路线详情：**
- 各路线行驶距离
- 车辆载重情况
- 迟到分析

---

## 四、API 调用示例

### 同步求解

```bash
curl -X POST "http://localhost:8000/api/v1/solve" \
  -H "Content-Type: application/json" \
  -d '{
    "customers": [
      {"id": 0, "name": "仓库", "lat": 39.9042, "lon": 116.4074, "demand": 0, "service_time_min": 0, "tw_earliest": 480, "tw_latest": 960},
      {"id": 1, "name": "客户A", "lat": 39.9123, "lon": 116.3456, "demand": 45, "service_time_min": 15, "tw_earliest": 500, "tw_latest": 600}
    ],
    "params": {
      "fuel_price": 7.5,
      "search_time_limit": 30
    }
  }'
```

### Python 调用

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/solve",
    json={
        "customers": [...],
        "params": {"search_time_limit": 30}
    }
)
result = response.json()
print(result)
```

---

## 五、Python 代码使用

### 基本求解

```python
import pandas as pd
from core.solver import GreenVRPSolver
from core.cost import calculate_green_cost
from config.vehicles import DEFAULT_VEHICLE_CONFIG

# 加载数据
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
cost_result = calculate_green_cost(solution, DEFAULT_VEHICLE_CONFIG, {})

# 输出结果
print(f"总距离: {solution['total_distance']:.2f} km")
print(f"总成本: {cost_result['total_cost']:.2f} 元")
print(f"碳排放: {cost_result['carbon_emission_kg']:.2f} kg CO2")
```

### 多策略求解

```python
from core.solver import solve_with_multiple_strategies

solution = solve_with_multiple_strategies(
    customers_df=df,
    vehicle_config=DEFAULT_VEHICLE_CONFIG,
    time_penalty_per_min=10.0,
    time_limit=60,
)
```

---

## 六、常见问题

### Q: 启动时提示模块找不到？
A: 确保在项目根目录运行，且已安装所有依赖：
```bash
pip install -r requirements.txt
```

### Q: 求解时间过长？
A: 减少求解时间限制，或减少客户数量。建议：
- 10 个客户以内：30 秒
- 10-20 个客户：60 秒
- 20-50 个客户：120 秒

### Q: 求解失败？
A: 检查数据格式，确保：
- 包含仓库（id=0）
- 时间窗有效（tw_earliest < tw_latest）
- 需求量不超过车辆容量

---

## 七、技术支持

- 问题反馈：提交 GitHub Issue
- 功能建议：提交 Pull Request

---

**祝您使用愉快！** 🚚🌿
