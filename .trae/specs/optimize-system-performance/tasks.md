# Tasks

- [ ] Task 1：建立性能基准测试体系
  - [ ] SubTask 1.1：创建前端基准脚本（Lighthouse + Web Vitals），输出到 `benchmarks/frontend/`
  - [ ] SubTask 1.2：创建 API 基准脚本（locust 或 httpx），覆盖 `/api/v1/solve`、场景 CRUD、健康检查，输出到 `benchmarks/api/`
  - [ ] SubTask 1.3：创建后端分析脚本（cProfile / py-spy），覆盖求解器与距离矩阵热点，输出到 `benchmarks/backend/`
  - [ ] SubTask 1.4：在 `benchmarks/README.md` 中定义基线指标、测试数据集与目标阈值

- [ ] Task 2：采集当前基线指标
  - [ ] SubTask 2.1：运行前端基准脚本，记录 Lighthouse 评分、LCP、主包大小、路由加载时间
  - [ ] SubTask 2.2：运行 API 基准脚本，记录 P50/P95/P99 响应时间与 RPS
  - [ ] SubTask 2.3：运行后端分析脚本，记录求解器/距离矩阵热点函数耗时

- [ ] Task 3：前端性能分析与优化
  - [ ] SubTask 3.1：使用 Vite/rollup 构建分析工具识别主包与大依赖
  - [ ] SubTask 3.2：针对重依赖（如 `recharts`）实施按需加载或进一步拆分
  - [ ] SubTask 3.3：优化图片/字体等静态资源（压缩、格式转换、CDN 配置评估）
  - [ ] SubTask 3.4：审查关键组件渲染性能，必要时使用 `memo`、虚拟化或状态切片
  - [ ] SubTask 3.5：重新运行前端基准，确认达到目标

- [ ] Task 4：后端性能分析与优化
  - [ ] SubTask 4.1：审查场景 CRUD 数据库查询，消除 N+1 与未索引查询
  - [ ] SubTask 4.2：分析距离矩阵缓存命中率与键生成效率，优化缓存策略
  - [ ] SubTask 4.3：分析求解器执行路径，减少重复计算与无效预热
  - [ ] SubTask 4.4：在合适位置增加 API 响应缓存（如场景列表）或请求合并
  - [ ] SubTask 4.5：重新运行 API 与后端基准，确认达到目标

- [ ] Task 5：多轮验证与回归测试
  - [ ] SubTask 5.1：第一轮验证：前端优化后单独跑通前端基准与 `npm run test`
  - [ ] SubTask 5.2：第二轮验证：后端优化后单独跑通 API 基准与 `pytest tests/`
  - [ ] SubTask 5.3：回归测试：完整运行 `pytest tests/` 与 `npm run test -- --run`

- [ ] Task 6：编写性能优化报告
  - [ ] SubTask 6.1：创建 `reports/Performance_Optimization_Report.md`
  - [ ] SubTask 6.2：包含基线数据、瓶颈分析、优化方案、前后对比、未达标项说明、后续建议

- [ ] Task 7：最终工程化验证
  - [ ] SubTask 7.1：运行 `ruff check .` 与 `mypy .`（允许既有模块冲突未修复）
  - [ ] SubTask 7.2：运行 `pytest tests/`
  - [ ] SubTask 7.3：运行 `cd web && npm run lint && npm run test -- --run && npm run build`

# Task Dependencies

- Task 2 依赖 Task 1
- Task 3 与 Task 4 可并行，均依赖 Task 2
- Task 5 依赖 Task 3 与 Task 4
- Task 6 依赖 Task 5
- Task 7 依赖 Task 6
