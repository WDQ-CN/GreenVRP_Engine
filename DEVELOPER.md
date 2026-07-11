# GreenVRP Engine 开发者指南

## 开发环境搭建

### 1. 前置要求

- Python 3.10+
- Git
- 推荐使用 VS Code 或 PyCharm

### 2. 环境配置

```bash
# 克隆仓库
git clone <repository-url>
cd green-vrp-engine

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# 安装依赖
pip install -e ".[dev]"

# 预提交钩子（可选）
pip install pre-commit
pre-commit install
```

### 3. IDE 配置

**VS Code 配置 (`.vscode/settings.json`)：**
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "files.exclude": {
        "__pycache__": true,
        "*.pyc": true,
        ".pytest_cache": true
    }
}
```

## 代码规范

### 1. 编码风格

遵循 PEP 8 规范：

```bash
# 格式化代码
python -m ruff format .

# 检查代码风格
python -m ruff check .

# 类型检查
python -m mypy api/ core/ optimization/ utils/ exceptions/ models/
```

### 2. 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `GreenVRPolver` |
| 函数名 | snake_case | `solve_vrp` |
| 变量名 | snake_case | `total_distance` |
| 常量 | UPPER_SNAKE | `MAX_VEHICLES` |
| 私有成员 | _snake_case | `_internal_method` |

### 3. 类型注解

建议使用类型注解：

```python
from typing import List, Dict, Optional

def solve_vrp(
    customers: List[Customer],
    vehicles: List[Vehicle],
    params: Dict[str, float]
) -> Optional[Solution]:
    """求解 VRP 问题"""
    pass
```

### 4. 文档字符串

使用 Google 风格文档字符串：

```python
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点间的 Haversine 距离。

    Args:
        lat1: 起点纬度
        lon1: 起点经度
        lat2: 终点纬度
        lon2: 终点经度

    Returns:
        两点间的距离（千米）

    Raises:
        ValueError: 坐标超出范围时
    """
    pass
```

## 项目结构

### 添加新模块

1. 在对应目录下创建模块文件
2. 添加 `__init__.py` 并导出公共接口
3. 编写单元测试
4. 更新文档

### 目录职责

| 目录 | 职责 |
|------|------|
| `core/` | 核心求解逻辑 |
| `optimization/` | 优化算法 |
| `analysis/` | 分析工具 |
| `tracking/` | 追踪功能 |
| `models/` | 数据模型 |
| `data_types/` | 数据类型定义 |
| `config/` | 配置管理 |
| `utils/` | 工具函数 |
| `exceptions/` | 异常定义 |
| `api/` | REST API |
| `frontend/` | 前端界面 |
| `tests/` | 测试代码 |

## 测试

### 单元测试

```python
# tests/unit/core/test_distance.py
import pytest
from core.distance import calculate_distance

def test_calculate_distance():
    """测试距离计算"""
    dist = calculate_distance(39.9042, 116.4074, 39.9142, 116.4174)
    assert dist > 0
    assert dist < 100
```

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定模块测试
python -m pytest tests/unit/core/test_distance.py -v

# 生成覆盖率报告
python -m pytest --cov=. --cov-report=html

# 查看覆盖率
# 打开 htmlcov/index.html
```

### 前端开发

前端位于 `web/` 目录，使用 Vite + React + TypeScript + Tailwind CSS：

```bash
cd web

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 代码检查
npm run lint

# 运行测试
npm run test

# 生产构建
npm run build
```

### 测试覆盖率要求

- 核心模块 (core/)：≥ 80%
- 优化模块 (optimization/)：≥ 70%
- 分析模块 (analysis/)：≥ 70%
- 追踪模块 (tracking/)：≥ 60%

## 调试

### 使用 pdb

```python
import pdb

def some_function():
    pdb.set_trace()  # 设置断点
    # 代码...
```

### 使用 VS Code 调试器

创建 `.vscode/launch.json`：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        }
    ]
}
```

### 日志调试

使用项目日志系统：

```python
import logging

logger = logging.getLogger(__name__)

def some_function():
    logger.info("开始处理...")
    logger.debug(f"参数值: {param}")
    logger.error("处理失败", exc_info=True)
```

## 性能优化

### 1. 使用缓存

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # 实现...
    pass
```

### 2. 使用向量化运算

```python
import numpy as np

# 避免循环，使用 numpy 向量化
def calculate_distances(coords1: np.ndarray, coords2: np.ndarray) -> np.ndarray:
    return np.linalg.norm(coords1 - coords2, axis=1)
```

### 3. 延迟导入

```python
def heavy_function():
    # 延迟导入重型库
    import pandas as pd
    import ortools
    # 使用...
```

## 版本管理

### 分支策略

- `main` - 主分支，稳定版本
- `develop` - 开发分支
- `feature/*` - 功能分支
- `bugfix/*` - 修复分支
- `release/*` - 发布分支

### 提交信息规范

使用 Conventional Commits：

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型：
- `feat` - 新功能
- `fix` - 修复
- `docs` - 文档
- `style` - 格式
- `refactor` - 重构
- `test` - 测试
- `chore` - 构建/工具

示例：
```
feat(solver): 添加多车型支持

实现异构车队的路径规划功能，支持混合车型调度。

Closes #123
```

### 提交流程

```bash
# 1. 拉取最新代码
git pull origin develop

# 2. 创建功能分支
git checkout -b feature/new-feature

# 3. 提交代码
git add .
git commit -m "feat: 添加新功能"

# 4. 推送分支
git push origin feature/new-feature

# 5. 创建 Pull Request
```

## 文档

### 代码文档

- 所有公共函数/类必须包含文档字符串
- 复杂逻辑添加行内注释
- 使用类型注解

### 更新文档

修改代码后，同步更新：
- README.md
- ARCHITECTURE.md
- DEVELOPER.md
- 相关函数的文档字符串

## 常见问题

### Q: 如何添加新的车型配置？

A: 在 `config/vehicles.py` 中添加：

```python
NEW_VEHICLE_TYPE = {
    "10m": {
        "capacity": 5000,
        "fixed_cost": 800,
        "fuel_per_100km": 35,
        "speed_kmh": 25,
    }
}
```

### Q: 如何添加新的成本维度？

A: 在 `core/cost.py` 中扩展 `calculate_green_cost` 函数。

### Q: 如何自定义优化策略？

A: 在 `optimization/` 下创建新模块，实现优化逻辑。

### Q: 如何添加新的 API 端点？

A: 在 `api/routers/` 下创建新路由文件，并在 `api/main.py` 中注册。

## 发布流程

### 1. 更新版本号

编辑 `config/constants.py`：

```python
VERSION = "1.2.0"
```

### 2. 更新 CHANGELOG.md

```markdown
## [1.2.0] - 2024-01-01

### Added
- 新功能 A
- 新功能 B

### Changed
- 优化 C

### Fixed
- 修复 D
```

### 3. 运行测试

```bash
pytest tests/
```

### 4. 创建发布分支

```bash
git checkout -b release/1.2.0
```

### 5. 合并到 main

```bash
git checkout main
git merge release/1.2.0
git tag v1.2.0
git push origin main --tags
```

## 贡献指南

1. Fork 仓库
2. 创建功能分支
3. 提交代码
4. 推送到分支
5. 创建 Pull Request

## 联系方式

- 项目主页: https://github.com/your-org/green-vrp-engine
- 问题反馈: https://github.com/your-org/green-vrp-engine/issues

## 许可证

MIT License
