# 更新日志 (CHANGELOG)

本文档记录了 GreenVRP Engine 的所有重要更改。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 规范化
- 统一 Python 代码风格：修复全部 Ruff 违规，配置 Ruff 排除项与 FastAPI B008 忽略
- 统一启动入口：删除 `start_fast.py`、`start_optimized.py`、`app.py`，`start.py` 作为唯一 CLI 入口
- 修复 `optimization/carbon_aware.py` 单元测试，使用 `MockSolverService` 替代裸函数
- 前端日志规范化：新增 `web/src/lib/logger.ts`，调试日志仅在开发环境输出
- 依赖管理：运行时依赖统一至 `pyproject.toml`
- 文档同步：更新 `README.md`、`DEVELOPER.md` 中的安装与启动说明

### 计划中
- 机器学习需求预测
- 多仓库支持
- 电动车辆充电规划
- 实时交通数据集成

## [1.0.0] - 2024-04-17

### 新增
- 核心 VRP 求解器 (core/solver.py)
- 五维成本核算 (core/cost.py)
- Haversine 和网格距离计算 (core/distance.py)
- 碳感知优化 (optimization/carbon_aware.py)
- 多目标优化 (optimization/multi_objective.py)
- 动态重规划 (optimization/dynamic.py)
- 场景对比分析 (analysis/comparison.py)
- 敏感度分析 (analysis/sensitivity.py)
- 策略效果评估 (analysis/strategy_eval.py)
- 实时位置追踪 (tracking/position_tracker.py)
- GPS 模拟器 (tracking/gps_simulator.py)
- ETA 预估 (tracking/eta_calculator.py)
- 电子围栏 (tracking/geofencing.py)
- REST API 接口 (api/)
- 标准 Web 界面 (web_app.py)
- 企业简约风格前端 (frontend/app.py)
- 高性能启动器 (start_fast.py)
- 完整的测试套件 (tests/)
- 数据模型层 (models/)
- 数据类型定义 (data_types/)
- 配置管理 (config/)
- 工具函数 (utils/)
- 自定义异常 (exceptions/)

### 文档
- README.md - 项目主文档
- QUICKSTART.md - 快速开始指南
- ARCHITECTURE.md - 架构文档
- DEVELOPER.md - 开发者指南
- CHANGELOG.md - 更新日志

### 技术栈
- Python 3.10+
- FastAPI 0.100.0+
- Streamlit 1.28.0+
- OR-Tools 9.7.0+
- Pandas 2.0.0+
- NumPy 1.24.0+
- Plotly 5.15.0+
- Folium 0.14.0+
- Pydantic 2.0.0+
- SQLAlchemy 2.0.0+
- Pytest

---

## 版本说明

版本号格式：`主版本号.次版本号.修订号`

- **主版本号**：不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

## 变更类型

- **新增** (Added) - 新增功能
- **变更** (Changed) - 功能变更
- **弃用** (Deprecated) - 即将移除的功能
- **移除** (Removed) - 已移除的功能
- **修复** (Fixed) - 问题修复
- **安全** (Security) - 安全相关修复
