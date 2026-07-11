# GreenVRP Engine 项目规范化计划

## 背景与目标

项目经过近几轮功能迭代（安全加固、前端重构、错误处理完善、distance bug 修复）后，代码功能趋于完整，但存在以下规范化债务：

1. Python 代码存在 50+ Ruff 规范问题；
2. 根目录入口文件（`start.py` / `start_fast.py` / `start_optimized.py` / `app.py` / `web_app.py`）职责重叠；
3. 后端 `optimization/carbon_aware.py` 与对应单元测试不匹配，导致 5 个测试持续失败；
4. 前端存在 `console.debug` 等调试输出，生产构建未剥离；
5. 文档、依赖、Docker 配置可进一步统一。

本计划目标是在不破坏现有功能的前提下，通过代码规范修复、入口统一、测试修复、前端清理和文档更新，把项目整理到可稳定维护的状态，并确保 `lint + test + build` 全部通过。

---

## 范围

本次规范化**不涉及**新功能开发，只包含：
- 代码风格与格式修复
- 入口脚本职责统一
- 现有失败测试修复
- 前端调试输出清理
- 文档和配置同步

---

## 阶段 1：Python 代码规范修复

### 1.1 修复可自动修复的 Ruff 问题

运行 `ruff check . --fix` 处理 import 排序、格式类问题。

代表文件：
- [api/dependencies.py](file:///d:/ZhuoMian/GreenVRP_Engine/api/dependencies.py)
- [core/__init__.py](file:///d:/ZhuoMian/GreenVRP_Engine/core/__init__.py)
- [optimization/carbon_aware.py](file:///d:/ZhuoMian/GreenVRP_Engine/optimization/carbon_aware.py)

### 1.2 手动修复剩余问题

| 文件 | 问题 | 修复方式 |
|------|------|---------|
| [api/routers/solver.py](file:///d:/ZhuoMian/GreenVRP_Engine/api/routers/solver.py) | B008 `Depends` 参数默认值 | 在 `pyproject.toml` 的 `[tool.ruff.lint]` 中增加 `B008` 忽略（FastAPI 官方推荐写法） |
| [frontend/config.py](file:///d:/ZhuoMian/GreenVRP_Engine/frontend/config.py) | C408 `dict()` 调用 | 改为字面量 `{}` |
| [optimization/carbon_aware.py](file:///d:/ZhuoMian/GreenVRP_Engine/optimization/carbon_aware.py) | SIM102 嵌套 if | 合并为单一 if 条件 |
| [optimization/multi_objective.py](file:///d:/ZhuoMian/GreenVRP_Engine/optimization/multi_objective.py) | N806 `BLOCK_SIZE` 函数内大写 | 改为 snake_case 的 `block_size` |
| [reports/generate_scan_report.py](file:///d:/ZhuoMian/GreenVRP_Engine/reports/generate_scan_report.py) | E741 歧义变量名 `l` | 改为有意义的变量名 |
| [start_fast.py](file:///d:/ZhuoMian/GreenVRP_Engine/start_fast.py) | E402 模块级导入不在顶部 | 在 `pyproject.toml` 增加 `start_fast.py` 的 E402 忽略，或调整导入顺序 |
| [start_optimized.py](file:///d:/ZhuoMian/GreenVRP_Engine/start_optimized.py) | T201 大量 `print` | 替换为 `logging`；保留启动横幅的少量输出，或在该文件顶部 `ruff: noqa: T20` |

### 1.3 配置 Ruff 排除项

在 [pyproject.toml](file:///d:/ZhuoMian/GreenVRP_Engine/pyproject.toml) 的 `[tool.ruff]` 中增加：

```toml
exclude = [".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "reports/security"]
```

避免扫描 `web/node_modules` 和报告脚本目录。

---

## 阶段 2：统一入口文件

### 2.1 现状分析

| 文件 | 当前职责 |
|------|---------|
| [start.py](file:///d:/ZhuoMian/GreenVRP_Engine/start.py) | CLI 选择器，可启动 web / api / solve |
| [start_fast.py](file:///d:/ZhuoMian/GreenVRP_Engine/start_fast.py) | 与 start.py 几乎重复，号称"快速启动" |
| [start_optimized.py](file:///d:/ZhuoMian/GreenVRP_Engine/start_optimized.py) | 更复杂的延迟导入/并行导入版本 |
| [app.py](file:///d:/ZhuoMian/GreenVRP_Engine/app.py) | Streamlit 旧入口（与 web_app.py 内容几乎一致） |
| [web_app.py](file:///d:/ZhuoMian/GreenVRP_Engine/web_app.py) | Streamlit 新入口 |

### 2.2 规范化方案

1. **保留** `start.py` 作为唯一 CLI 启动入口，整合 `api` / `web` / `solve` 三种模式。
2. **删除** `start_fast.py` 和 `start_optimized.py`，将其中有价值的延迟导入逻辑以可选方式合并到 `start.py`（如通过 `--lazy-import` 开关或环境变量）。
3. **保留** `web_app.py` 作为 Streamlit 入口。
4. **删除** `app.py`（与 `web_app.py` 重复）。
5. 在 [README.md](file:///d:/ZhuoMian/GreenVRP_Engine/README.md) 和 [DEVELOPER.md](file:///d:/ZhuoMian/GreenVRP_Engine/DEVELOPER.md) 中更新启动说明。

---

## 阶段 3：修复失败测试

### 3.1 问题定位

`tests/unit/optimization/test_carbon_aware.py` 5 个测试失败：

1. `test_init` 断言 `optimizer._solver_signature in ("new", "old")`，但 [optimization/carbon_aware.py](file:///d:/ZhuoMian/GreenVRP_Engine/optimization/carbon_aware.py) 已改为通过 `ISolverService` 接口调用，不再有此属性。
2. 其余 4 个测试失败原因：测试传入 `dummy_solver` 是裸函数，而 `_call_solver` 调用 `self.solver_service.solve_sync(...)`。

### 3.2 修复方案

方案 A（推荐）：更新测试，使其传入符合 `ISolverService` 接口的 mock 对象。

- 在 `tests/unit/optimization/test_carbon_aware.py` 中创建 `MockSolverService` 类，实现 `solve_sync` / `solve_async` 方法。
- 删除对 `_solver_signature` 的断言。
- 若 `CarbonAwareOptimizer.__init__` 仍接受旧函数签名，则保持兼容；否则统一改为只接受 `ISolverService`。

方案 B：修改 `CarbonAwareOptimizer` 兼容裸函数求解器。

- 在 `__init__` 中检测 `solver_service` 是函数还是对象，自动包装。

建议采用**方案 A**，因为 [optimization/carbon_aware.py](file:///d:/ZhuoMian/GreenVRP_Engine/optimization/carbon_aware.py) 的 docstring 和 `_call_solver` 已明确面向 `ISolverService`，测试应同步更新。

---

## 阶段 4：前端清理

### 4.1 移除/控制调试输出

搜索并处理以下文件中的 `console.debug` / `console.log` / `console.warn`：

- [web/src/lib/repositories/solverRepository.ts](file:///d:/ZhuoMian/GreenVRP_Engine/web/src/lib/repositories/solverRepository.ts)
- [web/src/lib/solver.ts](file:///d:/ZhuoMian/GreenVRP_Engine/web/src/lib/solver.ts)
- [web/src/hooks/useSolveExecution.ts](file:///d:/ZhuoMian/GreenVRP_Engine/web/src/hooks/useSolveExecution.ts)
- [web/src/pages/WorkspacePage.tsx](file:///d:/ZhuoMian/GreenVRP_Engine/web/src/pages/WorkspacePage.tsx)

处理原则：
- 生产构建保留用户可见的错误日志；
- 调试日志通过 `import.meta.env.DEV` 包裹，或统一替换为 `logger.debug`；
- 删除已废弃的临时日志。

### 4.2 检查并修复类型导出的完整性

- [web/src/types/index.ts](file:///d:/ZhuoMian/GreenVRP_Engine/web/src/types/index.ts) 已较完整，检查是否有遗漏字段（如 SolveResponse 中 `error_message`）。
- 确保所有组件 props 都有明确类型，不使用隐式 `any`。

---

## 阶段 5：配置与文档同步

### 5.1 .gitignore

检查 [d:/ZhuoMian/GreenVRP_Engine/.gitignore](file:///d:/ZhuoMian/GreenVRP_Engine/.gitignore) 是否已包含：

```gitignore
.ruff_cache/
.mypy_cache/
.streamlit/
```

当前已包含，无需修改。

### 5.2 依赖管理

- [requirements.txt](file:///d:/ZhuoMian/GreenVRP_Engine/requirements.txt) 与 [pyproject.toml](file:///d:/ZhuoMian/GreenVRP_Engine/pyproject.toml) 的 `project.dependencies` 可能存在重复/不一致。
- 推荐将运行时依赖统一迁移到 `pyproject.toml` 的 `[project] dependencies`，`requirements.txt` 改为从 `pyproject.toml` 导出或删除。
- 保留 `requirements-test.txt` 作为向后兼容，但推荐仅使用 `pip install -e ".[dev]"`。

### 5.3 文档更新

- [README.md](file:///d:/ZhuoMian/GreenVRP_Engine/README.md)：更新启动命令为唯一的 `python start.py`。
- [DEVELOPER.md](file:///d:/ZhuoMian/GreenVRP_Engine/DEVELOPER.md)：补充 lint、test、build 命令和目录结构说明。
- [CHANGELOG.md](file:///d:/ZhuoMian/GreenVRP_Engine/CHANGELOG.md)：记录本次规范化内容（如用户要求）。

---

## 阶段 6：验证

每完成一个阶段即运行对应验证：

| 阶段 | 验证命令 | 通过标准 |
|------|---------|---------|
| Python 规范 | `python -m ruff check .` | 0 错误 |
| Python 类型 | `python -m mypy api/ core/ optimization/ utils/ exceptions/ models/` | 类型错误数不增加（当前基线） |
| 后端测试 | `python -m pytest tests/unit -q` | 全部通过 |
| 入口脚本 | `python start.py --help` | 正常输出 |
| 前端 lint | `cd web && npm run lint` | 0 错误 |
| 前端测试 | `cd web && npm run test -- --run` | 全部通过 |
| 前端构建 | `cd web && npm run build` | 成功 |
| 文档 | 人工检查 README / DEVELOPER.md | 无过期命令 |

---

## 风险与回滚

1. **入口文件删除风险**：`start_fast.py` / `start_optimized.py` / `app.py` 删除后，若外部脚本依赖它们会失败。修复方式：在 README 中声明；如不确定是否被引用，可先重命名为 `.bak` 再观察。
2. **测试语义变更**：更新 `test_carbon_aware.py` 可能改变测试意图。修复方式：仅将 `dummy_solver` 包装为 `MockSolverService`，不改变优化算法断言。
3. **Ruff 规则变更**：忽略 B008 会降低规则严格度，但这是 FastAPI 生态的常规做法。

---

## 建议执行顺序

1. 阶段 1（Python 规范）→ 阶段 3（测试修复）→ 阶段 2（入口统一）→ 阶段 4（前端清理）→ 阶段 5（文档）。
2. 每个阶段单独验证，确保不引入回归。
3. 全部完成后做一次端到端 `lint + test + build` 全量验证。
