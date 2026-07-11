# 内存安全改进验证与清理计划

## Summary

本计划针对 GreenVRP Engine 的三个内存安全改进点进行验证、清理与收尾：
1. `SolverService` 后台任务数量上限与优雅关闭逻辑；
2. 缓存中 `deepcopy` 替换为轻量 JSON 序列化 / `model_dump` 重建策略，并补充内存基准测试；
3. `RateLimitMiddleware` 的 IP 条目上限与过期清理，防止海量伪造 IP 导致内存无限增长。

经 Phase 1 探索，三个功能的核心代码已在仓库中实现。本计划目标是通过测试、lint、基准测试等手段验证实现正确性，修复回归问题，并输出验证结论。

## Current State Analysis

### 已实现内容

- `api/services/solver_service.py`:
  - `__init__` 中引入 `_background_tasks: set[asyncio.Task]`、`_bg_task_lock`、`_max_background_tasks`（默认从 `GREENVRP_MAX_BACKGROUND_TASKS` 读取，默认 10）、`_shutdown_timeout`、`_shutdown_event`。
  - `solve_async` 在 `_shutdown_event` 已设置或任务数达到上限时抛出 `ServiceUnavailableError`。
  - `close()` 设置关闭标志，等待后台任务完成，超时后取消未完成任务。
  - 求解结果缓存已改为 `_serialize_result` / `_deserialize_result`：优先 JSON 序列化，不可序列化时回退 `deepcopy`。

- `api/routers/scenarios.py`:
  - 场景列表缓存已从 `deepcopy` 替换为 `_serialize_scenarios`（`model_dump`）+ `_deserialize_scenarios`（Pydantic 重建）。

- `api/middleware/security.py`:
  - `RateLimitMiddleware` 增加 `max_ips`（默认从 `GREENVRP_RATE_LIMIT_MAX_IPS` 读取，默认 10000）。
  - 增加 `_purge_expired_ips` 过期清理。
  - 使用 `asyncio.Lock` 保护 `_requests` 字典。
  - 支持 `disabled` 参数用于测试。

- `benchmarks/backend/bench_cache_memory.py`:
  - 已存在，对比 deepcopy / JSON 反序列化 / `model_copy(deep=True)` / `model_dump`+重建 的内存与耗时。

- 测试与依赖:
  - `tests/unit/api/test_solver_service_lifecycle.py` 已覆盖任务上限、关闭等待、超时取消、关闭后拒绝新任务。
  - `tests/unit/api/test_scenarios_cache.py` 已覆盖缓存隔离。
  - `tests/integration/test_api_security.py` 已覆盖限流、X-Forwarded-For、IP 上限、过期清理。
  - `tests/conftest.py` 已设置 `GREENVRP_RATE_LIMIT_DISABLED=true`、`GREENVRP_API_KEY` 等环境变量，并添加 `_reset_solver_service` autouse fixture。
  - `api/main.py` lifespan 已调用 `_solver_service.close()`。
  - `exceptions/errors.py` 已定义 `ServiceUnavailableError`。

### 潜在风险

- `SolverService.close()` 中的 `asyncio.gather(*self._background_tasks, return_exceptions=True)` 在取消后可能仍访问已被 `discard` 的任务集合，需验证是否稳定。
- 测试使用 `monkeypatch` 替换 `_execute_job`，但真实路径中 `_execute_job` 调用 `solve_sync`，需确保缓存 JSON 序列化不会破坏真实返回结构。
- `RateLimitMiddleware` 在达到 `max_ips` 时触发全量清理，若伪造 IP 持续涌入，仍可能频繁清理，需通过测试验证行为。
- 基准测试脚本可能依赖 `api.schemas.response.ScenarioResponse`，需确认该模块存在且可导入。
- 可能遗留临时文件（如 `parse_bandit_tmp.py`）或 Ruff/ESLint 未修复的格式问题。

## Proposed Changes

### 1. 运行测试验证（高优先级）

**What**: 运行与本次改动相关的单元测试和集成测试。
**Files**: 不修改代码，仅执行命令。
**How**:
- 运行 `pytest tests/unit/api/test_solver_service_lifecycle.py -v`
- 运行 `pytest tests/unit/api/test_scenarios_cache.py -v`
- 运行 `pytest tests/integration/test_api_security.py::TestRateLimit -v`
- 运行全量 Python 测试 `pytest tests/ -q`（确认无回归）

**Why**: 确保已实现的逻辑通过现有回归测试，并发现潜在并发、生命周期或缓存隔离问题。

### 2. 运行代码质量检查（高优先级）

**What**: 运行 Ruff 检查与格式化、Prettier/ESLint（前端）。
**Files**: 不修改代码，先执行检查命令；若发现问题再按规则修复。
**How**:
- `ruff check . --fix`
- `ruff format .`
- `npm run lint`（前端，若 package.json 存在）
- `npm run format`（前端，可选）

**Why**: 项目约定 Python 代码必须满足 Ruff 规则，前端日志仅在开发环境输出。清理可避免提交前的格式与规范问题。

### 3. 运行内存基准测试（中优先级）

**What**: 执行 `benchmarks/backend/bench_cache_memory.py`，确认脚本可运行并生成结果。
**Files**: `benchmarks/backend/bench_cache_memory.py`、输出目录 `benchmarks/backend/results/cache_memory_benchmark.json`。
**How**:
- `python benchmarks/backend/bench_cache_memory.py`
- 检查输出 JSON 中 deepcopy 与 JSON/model_dump 策略的 peak_kb / elapsed_ms 差异。

**Why**: 验证“替换 deepcopy 后更轻量”这一假设是否有数据支撑，并发现脚本中可能的导入或运行时错误。

### 4. 修复测试与 lint 发现的问题（按需）

**What**: 根据步骤 1-3 的输出，修复失败用例、Ruff/ESLint 错误、基准测试异常。
**可能涉及的文件**（仅为示例，根据实际输出确定）：
- `api/services/solver_service.py`：若 `close()` 在取消后访问已清理任务集合引发异常，需调整 `gather` 调用顺序或复制集合。
- `api/middleware/security.py`：若存在 Ruff 警告（如循环变量绑定、未使用导入）则修复。
- `benchmarks/backend/bench_cache_memory.py`：若存在 B023 等 lambda 绑定警告，按之前经验显式捕获循环变量。
- `tests/conftest.py`：若 E402 等导入顺序问题复现，调整导入顺序。
- 删除临时文件，如 `parse_bandit_tmp.py`（若存在）。

**Why**: 保证代码库在功能、安全、格式三个维度都符合项目约定。

### 5. 生成验证报告（低优先级）

**What**: 汇总测试结果、lint 结果、基准测试关键数据，写入 `reports/memory_safety_validation.md`。
**Files**: 新建 `reports/memory_safety_validation.md`。
**How**:
- 记录 Python 测试通过数/失败数。
- 记录 Ruff/ESLint 是否通过。
- 记录基准测试关键对比数据。
- 列出修复的问题和未解决的遗留项（如 mypy/Bandit 历史问题）。

**Why**: 项目约定需要详细的迭代报告，包含问题清单、解决方案、优化效果和后续建议。

## Assumptions & Decisions

1. **不重构已实现的核心逻辑**：当前 `SolverService`、场景缓存、`RateLimitMiddleware` 的核心实现已与用户要求一致，本阶段以验证和清理为主。
2. **测试环境依赖 `tests/conftest.py`**：所有共享环境变量（API Key、限流禁用、CORS 来源）已集中配置，不单独在测试文件中修改。
3. **Ruff 规则优先**：修复时遵循项目现有的 Ruff 配置与排除项，B008 在路由依赖注入中已标记 noqa。
4. **基准测试输出为参考数据**：不将基准测试脚本纳入 CI 强制阈值，仅用于验证策略效果。
5. **前端 lint 作为清理项**：本次改动主要在后端，但按项目约定仍运行前端 lint 以发现潜在回归。

## Verification Steps

1. 运行相关单元测试并确认全部通过：
   - `pytest tests/unit/api/test_solver_service_lifecycle.py -v`
   - `pytest tests/unit/api/test_scenarios_cache.py -v`
2. 运行限流集成测试并确认全部通过：
   - `pytest tests/integration/test_api_security.py::TestRateLimit -v`
3. 运行全量 Python 回归测试并确认通过：
   - `pytest tests/ -q`
4. 运行 Ruff 检查与格式化并确认无残留错误：
   - `ruff check .`
   - `ruff format . --check`
5. 运行前端 lint 并确认无新增错误：
   - `npm run lint`
6. 运行内存基准测试并确认脚本成功生成结果文件：
   - `python benchmarks/backend/bench_cache_memory.py`
   - 检查 `benchmarks/backend/results/cache_memory_benchmark.json`
7. （可选）生成验证报告 `reports/memory_safety_validation.md`。

## Rollback Plan

- 所有修改均为本地文件编辑，可通过 `git diff` 审查，必要时 `git checkout -- <file>` 回滚单个文件。
- 若测试失败根因为已实现逻辑设计缺陷，且修复涉及较大改动，则先记录问题并通知用户，不擅自重写核心逻辑。
