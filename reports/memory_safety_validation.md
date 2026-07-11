# 内存安全改进验证报告

**验证日期**: 2026-06-30  
**验证范围**: SolverService 后台任务上限与优雅关闭、缓存 deepcopy 替换为序列化策略、RateLimitMiddleware IP 条目上限与过期清理。

## 1. 测试验证结果

### 1.1 相关单元与集成测试

| 测试文件 | 用例数 | 通过数 | 失败数 |
| --- | --- | --- | --- |
| `tests/unit/api/test_solver_service_lifecycle.py` | 4 | 4 | 0 |
| `tests/unit/api/test_solver_service_cache.py` | 2 | 2 | 0 |
| `tests/unit/api/test_scenarios_cache.py` | 1 | 1 | 0 |
| `tests/integration/test_api_security.py::TestRateLimit` | 5 | 5 | 0 |
| **全量 Python 测试** | **135** | **135** | **0** |

覆盖点：
- `SolverService.solve_async` 在后台任务数达到上限时抛出 `ServiceUnavailableError`。
- `SolverService.close()` 可等待任务完成，超时后取消未完成任务。
- 关闭事件设置后，`solve_async` 拒绝新任务。
- 求解结果缓存使用 JSON 序列化/反序列化后，调用方修改不污染缓存；不可序列化类型可降级为 deepcopy。
- 场景列表缓存使用 `model_dump` + 重建后，调用方修改不污染缓存。
- `RateLimitMiddleware` 正确识别 X-Forwarded-For、限制单 IP 请求频率、限制总 IP 条目数、清理过期 IP。

### 1.2 测试环境

- Python 3.14.6
- pytest 9.1.0
- 测试环境变量由 `tests/conftest.py` 统一配置：
  - `GREENVRP_API_KEY=test-api-key-12345`
  - `GREENVRP_RATE_LIMIT_DISABLED=true`
  - `GREENVRP_ALLOWED_ORIGINS=http://localhost:3000`

## 2. 代码质量检查结果

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| `ruff check .` | 通过 | 修复前存在 2 个错误，已修复 |
| `ruff format . --check` | 通过 | 已格式化 4 个文件 |
| `npm run lint` (web 目录) | 通过 | ESLint 无错误 |

### 2.1 已修复问题

1. **`tests/unit/api/test_solver_service_cache.py`**: 删除未使用的 `import pytest`。
2. **`tests/unit/api/test_solver_service_lifecycle.py`**: 新增 `import contextlib`，将 `try/except asyncio.CancelledError/pass` 改写为 `with contextlib.suppress(asyncio.CancelledError)`，符合 SIM105 规则。
3. **格式化文件**: `api/middleware/security.py`、`api/services/solver_service.py`、`benchmarks/backend/bench_cache_memory.py`、`tests/integration/test_api_security.py`。

### 2.2 遗留问题

- `pytest.ini` 与 `pyproject.toml` 中的 pytest 配置冲突，当前以 `pytest.ini` 为准，系统提示忽略 `pyproject.toml` 中的配置。
- 运行测试时出现若干 `DeprecationWarning`（SWIG 相关）和 `PytestConfigWarning`（未知配置项 `asyncio_default_fixture_loop_scope`、`asyncio_mode`），不影响测试通过，但建议在后续迭代中清理。

## 3. 内存基准测试结果

执行命令:

```bash
python benchmarks/backend/bench_cache_memory.py
```

结果文件: `benchmarks/backend/results/cache_memory_benchmark.json`

### 3.1 求解结果缓存对比（100 次迭代）

| 规模 | 策略 | 耗时 (ms) | 峰值内存 (KB) |
| --- | --- | --- | --- |
| 10 routes | deepcopy | 33.67 | 32.02 |
| 10 routes | json_deserialize | 30.01 | 34.91 |
| 100 routes | deepcopy | 365.59 | 300.78 |
| 100 routes | json_deserialize | 329.74 | 325.50 |
| 500 routes | deepcopy | 2134.32 | 1633.59 |
| 500 routes | json_deserialize | 2283.91 | 1623.17 |

**结论**: 在中等规模（10/100 routes）下，JSON 反序列化略快；在 500 routes 下两者接近，JSON 反序列化内存略低。整体差异不显著，但 JSON 策略提供了更彻底的数据隔离。

### 3.2 场景响应缓存对比（100 次迭代）

| 规模 | 策略 | 耗时 (ms) | 峰值内存 (KB) |
| --- | --- | --- | --- |
| 10 items | pydantic_deepcopy | 17.97 | 9.80 |
| 10 items | model_dump_rebuild | 2.65 | 10.68 |
| 100 items | pydantic_deepcopy | 242.90 | 87.01 |
| 100 items | model_dump_rebuild | 35.30 | 108.48 |
| 500 items | pydantic_deepcopy | 891.89 | 433.98 |
| 500 items | model_dump_rebuild | 183.86 | 539.82 |

**结论**: `model_dump` + Pydantic 重建比 `model_copy(deep=True)` 快约 5-7 倍，内存占用增加约 20-25%。在场景列表缓存这种读取频繁、数据规模中等的场景下，时间收益显著。

## 4. 核心文件变更确认

| 文件 | 状态 | 关键内容 |
| --- | --- | --- |
| `api/services/solver_service.py` | 已实现 | 后台任务上限、优雅关闭、JSON 序列化缓存（回退 deepcopy） |
| `api/routers/scenarios.py` | 已实现 | `model_dump` + 重建替代 deepcopy |
| `api/middleware/security.py` | 已实现 | `max_ips`、过期清理、`asyncio.Lock` |
| `benchmarks/backend/bench_cache_memory.py` | 已实现 | 内存与耗时基准测试 |
| `tests/unit/api/test_solver_service_lifecycle.py` | 已修复 lint | 生命周期测试 |
| `tests/unit/api/test_solver_service_cache.py` | 已修复 lint | 缓存隔离与降级测试 |
| `tests/unit/api/test_scenarios_cache.py` | 已实现 | 场景缓存隔离测试 |
| `tests/integration/test_api_security.py` | 已格式化 | 限流集成测试 |
| `tests/conftest.py` | 已实现 | 环境变量与 SolverService 重置 fixture |
| `api/main.py` | 已实现 | lifespan 关闭 SolverService |
| `api/dependencies.py` | 已实现 | `reset_solver_service` |
| `exceptions/errors.py` | 已实现 | `ServiceUnavailableError` |

## 5. 后续建议

1. **统一 pytest 配置**: 解决 `pytest.ini` 与 `pyproject.toml` 的冲突，将 pytest 配置集中到一个文件中。
2. **清理警告**: 处理 SWIG 相关的 `DeprecationWarning` 和 pytest 配置项警告。
3. **CI 加固**: 在 CI 中增加 `ruff check`、`ruff format --check` 和 `npm run lint` 门禁，防止未修复的格式问题合入。
4. **基准测试 CI 化（可选）**: 将 `bench_cache_memory.py` 纳入 CI 作为非阻塞的参考步骤，定期跟踪缓存策略性能。
5. **限流持久化（可选）**: 当前限流为内存实现，生产环境建议评估 Redis 等外部存储，以支持多实例部署。

## 6. 总结

本次验证与清理工作确认：三个内存安全改进点的核心实现已经正确落地，所有相关回归测试通过，代码质量检查通过，内存基准测试完成并生成对比数据。仅在测试文件中修复了 2 个 Ruff 问题，并对 4 个文件进行了格式化，未引入新的回归。
