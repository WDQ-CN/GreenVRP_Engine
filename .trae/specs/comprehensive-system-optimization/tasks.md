# Tasks

- [x] Task 1：后端安全加固
  - [x] SubTask 1.1：将 `core/distance.py` 与 `core/solver.py` 中的 `hashlib.md5` 替换为 `hashlib.sha256`（或 `blake2b`）并删除 MD5 导入
  - [x] SubTask 1.2：修改 `api/middleware/security.py`，当 `GREENVRP_API_KEY` 未配置且 `GREENVRP_ALLOW_UNAUTHENTICATED` 不为 `true` 时，对健康检查外所有请求返回 401
  - [x] SubTask 1.3：在 `api/main.py` 中配置 `Request`/`Multipart` 最大请求体大小限制，并新增全局 500 异常处理器确保不泄露堆栈
  - [x] SubTask 1.4：为 `api/services/solver_service.py` 的 `_validate_callback_url` 补充单测，覆盖私有 IP、localhost、内网域名与非法协议
  - [x] SubTask 1.5：运行 `pytest tests` 与 `test_api_security.py`，确保认证/限流/异常脱敏行为正确

- [ ] Task 2：后端代码质量整治（Ruff + MyPy）
  - [ ] SubTask 2.1：在 `core/`、`utils/`、`config/`、`data_types/`、`api/routers/`、`api/services/`、`api/schemas/`、`exceptions/` 中运行 `ruff check . --fix`，处理所有自动修复项
  - [ ] SubTask 2.2：手动修复剩余 Ruff 问题（UP006/UP007/UP045 类型注解现代化、F401 未使用导入、T201 print 语句、B007 未使用循环变量等）
  - [ ] SubTask 2.3：修复 MyPy 在 `core/distance.py`、`core/solver.py`、`optimization/dynamic.py`、`data_types/solution.py` 中的高频类型错误
  - [ ] SubTask 2.4：对 Radon 复杂度 ≥ C 的函数进行拆分或重构，重点处理 `core/cost.py:_get_vehicle_params_cached_impl`、`utils/validation.py:validate_customer`、`analysis/comparison.py:ScenarioComparison.compare_solutions`
  - [ ] SubTask 2.5：运行 `ruff check .`、`mypy .` 与 `pytest tests/unit`，确认问题数显著下降且测试通过

- [x] Task 3：求解器与距离矩阵性能优化
  - [x] SubTask 3.1：重构 `core/distance.py` 中 `DistanceMatrixCache._hash_locations`，使用更稳定的序列化方式（如 `json.dumps` + SHA-256）生成缓存键
  - [x] SubTask 3.2：清理 `core/solver.py` 中 `SolverPool` 未真正使用的求解器实例池，保留解决方案缓存并简化接口
  - [x] SubTask 3.3：修复 `build_distance_matrix` 在大规模节点下返回 `SparseDistanceMatrix` 后，`build_time_matrix` 无法直接消费的问题（禁用自动稀疏或实现 `to_dense` 转换）
  - [x] SubTask 3.4：为 `core/distance.py` 与 `core/solver.py` 补充性能相关单元测试（缓存命中、稀疏矩阵回退）
  - [x] SubTask 3.5：运行 `pytest tests/unit/core`，确认求解器与距离计算测试全部通过

- [ ] Task 4：场景数据持久化
  - [ ] SubTask 4.1：在 `models/database.py` 中确认 SQLite 不设置 `check_same_thread=False`，并暴露 `init_db()` / `get_db()`
  - [ ] SubTask 4.2：新增/修改 `models/scenario.py` 的 SQLAlchemy 模型，字段与现有 `ScenarioCreate`/`ScenarioUpdate`  schema 对齐
  - [ ] SubTask 4.3：重写 `api/routers/scenarios.py`，使用数据库会话完成 CRUD；删除内存 `_scenarios_db` 与 `_scenario_counter`
  - [ ] SubTask 4.4：在 `api/main.py` 的 lifespan 中调用 `init_db()`，确保启动时创建表
  - [ ] SubTask 4.5：补充 `tests/unit/api/test_scenarios.py` 或扩展现有测试，覆盖创建、列表、详情、更新、删除及重启后数据保留
  - [ ] SubTask 4.6：运行 `pytest tests/unit/api` 与 `test_api_integration.py`，确认场景接口正常

- [x] Task 5：前端性能优化（代码分割）
  - [x] SubTask 5.1：将 `web/src/router/index.tsx` 中的页面组件改为 `React.lazy` 导入，并用 `Suspense` 包裹路由节点，提供统一 fallback
  - [x] SubTask 5.2：在 `web/vite.config.ts` 中配置 `build.rollupOptions.output.manualChunks`，将 `recharts`、Radix UI、React 生态等拆分为独立 chunk
  - [x] SubTask 5.3：运行 `npm run build`，确认主 chunk < 500 KB；若仍超标，进一步拆分大页面或动态加载 `recharts`
  - [x] SubTask 5.4：运行 `npm run lint` 与 `npm run test`，确认无新增报错

- [x] Task 6：前端体验与可访问性增强
  - [x] SubTask 6.1：新增全局 `ErrorBoundary` 组件，并在 `RouterProvider` 外层包裹，捕获渲染错误并展示友好提示
  - [x] SubTask 6.2：为 `web/src/components/ui/tabs.tsx` 的 `TabsTrigger` 补充 `aria-label` 或确保 value 被正确识别；修复自动化测试中"unrecognized TabsTrigger"警告
  - [x] SubTask 6.3：在 `web/src/lib/api.ts` 中统一 401/403/500/网络错误提示，避免直接暴露后端原始错误
  - [x] SubTask 6.4：运行 `npm run test` 与浏览器关键路径验证（工作台 → 求解 → 结果 Tab 切换）

- [ ] Task 7：工程化、CI 与文档
  - [ ] SubTask 7.1：修复 `.github/workflows/ci.yml` 中 `ruff --version` / `ruff check .` 的命令（已为小写则保持不变）
  - [ ] SubTask 7.2：在 CI 中增加 `npm ci && npm run lint && npm run test && npm run build` 步骤
  - [ ] SubTask 7.3：更新 `ARCHITECTURE.md` 中场景持久化、前端路由懒加载、安全中间件相关描述
  - [ ] SubTask 7.4：更新 `CHANGELOG.md`，记录本次优化的问题清单、解决方案、优化效果与后续建议
  - [ ] SubTask 7.5：运行完整后端 `pytest` 与前端 `npm run build && npm run test`，生成最终验证报告

# Task Dependencies

- Task 4 依赖 Task 1（场景接口仍需认证/限流通过）
- Task 5 与 Task 6 可并行
- Task 7 依赖 Task 1 ~ Task 6 全部完成
