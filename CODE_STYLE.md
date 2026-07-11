# GreenVRP Engine 代码规范指南

## 1. 代码格式化工具

本项目使用以下工具保持代码风格一致：

- **Black**: 代码格式化（行宽 100 字符）
- **isort**: 导入排序（Black 兼容模式）
- **flake8**: 代码风格检查
- **mypy**: 类型检查

### 安装开发工具

```bash
pip install black isort flake8 mypy
```

### 格式化代码

```bash
# 排序导入
isort .

# 格式化代码
black .

# 检查代码风格
flake8 .

# 类型检查
mypy .
```

## 2. 配置说明

所有工具配置已统一在 `pyproject.toml` 文件中：

- 行宽限制：100 字符
- Python 版本：3.8+
- 导入排序：Black 兼容模式

## 3. 编码规范

### 3.1 命名约定

- **类名**: PascalCase (如 `VehicleCostParams`)
- **函数/变量**: snake_case (如 `calculate_total_cost`)
- **常量**: UPPER_CASE (如 `DEFAULT_CARBON_PRICE`)
- **私有成员**: 前缀下划线 (如 `_internal_cache`)

### 3.2 类型注解

所有公共函数必须添加类型注解：

```python
from typing import Dict, List, Optional

def calculate_cost(
    routes: List[List[int]],
    distance_matrix: np.ndarray,
    config: Dict[str, Any]
) -> Dict[str, float]:
    """计算总成本。"""
    pass
```

### 3.3 文档字符串

使用 Google 风格文档字符串：

```python
def function_name(param1: str, param2: int) -> bool:
    """简短描述功能。

    详细描述（可选）。

    Args:
        param1: 参数 1 描述
        param2: 参数 2 描述

    Returns:
        返回值描述

    Raises:
        ValueError: 异常情况说明
    """
    pass
```

### 3.4 导入顺序

1. 标准库
2. 第三方库
3. 本地模块

每组之间空一行，组内按字母排序。

## 4. 常见错误修复

### 4.1 未使用的 global 声明

错误示例：
```python
def func():
    global cache  # 如果只读取不赋值，不需要 global
    return cache[key]
```

正确做法：
```python
def func():
    return cache[key]  # 只读访问不需要 global
```

### 4.2 未定义的变量

确保循环变量正确定义：
```python
# 错误
for item in items:
    result = i * 2  # i 未定义

# 正确
for i, item in enumerate(items):
    result = i * 2
```

### 4.3 引号不匹配

确保字符串引号成对：
```python
# 错误
config = {'key": value}

# 正确
config = {'key': value}
```

## 5. Git 提交前检查清单

- [ ] 运行 `black .` 格式化代码
- [ ] 运行 `isort .` 排序导入
- [ ] 运行 `flake8 .` 无严重错误
- [ ] 运行 `python -m py_compile` 语法检查通过
- [ ] 添加必要的类型注解
- [ ] 更新文档字符串

## 6. CI/CD 集成

建议在 CI 流程中加入自动化检查：

```yaml
# GitHub Actions 示例
- name: Code Quality Check
  run: |
    pip install black isort flake8 mypy
    black --check .
    isort --check-only .
    flake8 . --count --select=E9,F63,F7,F82
    mypy . --ignore-missing-imports
```
