# 系统性性能优化 Spec

## Why

当前项目缺少统一的性能基准与持续监控体系，前端生产构建体积、页面加载耗时、API 响应延迟及求解器执行效率均未建立可量化的基线。为了提升用户体验与系统吞吐能力，需要建立基准测试体系，识别关键瓶颈，实施针对性优化，并将关键性能指标控制在当前水平的 80% 以内（即整体提升 20% 以上）。

## What Changes

- 建立前后端统一的性能基准测试脚本与指标采集流程。
- 使用 Lighthouse、Chrome DevTools、Vite 构建分析等工具识别前端性能瓶颈。
- 使用 cProfile、py-spy、数据库查询分析等工具识别后端瓶颈。
- 优化前端资源加载策略（chunk 拆分、懒加载、图片/字体压缩、依赖按需加载）。
- 优化后端代码执行效率（求解器路径、距离矩阵缓存、数据库查询、API 响应缓存）。
- 进行多轮基准测试与回归测试，确保优化效果稳定。
- 编写性能优化报告，记录基线、瓶颈、优化手段、效果与后续建议。

## Impact

- **受影响功能**：前端页面加载与交互、API 响应速度、求解器执行、场景数据持久化。
- **关键文件/目录**：
  - `web/`（构建配置、路由、组件、依赖）
  - `api/`（路由、服务、中间件）
  - `core/`（求解器、距离矩阵）
  - `models/`（数据库模型与查询）
  - `scripts/` 或 `benchmarks/`（新增基准脚本）
  - `reports/Performance_Optimization_Report.md`（新增报告）

## ADDED Requirements

### Requirement: 性能基准测试体系

The system SHALL provide repeatable benchmark scripts for frontend, API, and backend solver performance.

#### Scenario: 前端基准

- **WHEN** 运行前端基准脚本
- **THEN** 输出 Lighthouse 评分、Web Vitals（LCP、INP、CLS）、各路由首次加载时间

#### Scenario: API 基准

- **WHEN** 运行 API 基准脚本
- **THEN** 输出关键接口（`/api/v1/solve`、`/api/v1/scenarios` 等）的 P50/P95/P99 响应时间与吞吐量

#### Scenario: 后端分析

- **WHEN** 运行求解器/距离矩阵分析脚本
- **THEN** 输出热点函数、调用次数与累计耗时

### Requirement: 性能目标

The system SHALL achieve the following targets relative to the established baseline:

- 前端 Lighthouse Performance 评分 ≥ 80（基线若低于则提升 20%）。
- 首屏 LCP 控制在基线的 80% 以内。
- `/api/v1/solve` 同步模式 P95 响应时间控制在基线的 80% 以内。
- `/api/v1/scenarios` 列表查询 P95 响应时间控制在基线的 80% 以内。
- 求解器 CPU 耗时（相同数据集）控制在基线的 80% 以内。

### Requirement: 性能优化报告

The system SHALL produce `reports/Performance_Optimization_Report.md` documenting baseline metrics, identified bottlenecks, optimizations applied, final metrics, and follow-up recommendations.

## MODIFIED Requirements

### Requirement: 前端资源加载策略

前端生产构建 SHALL continue to split chunks and lazy-load routes, and SHALL further optimize heavy dependencies and assets where benchmarks identify bottlenecks.

### Requirement: 后端缓存与查询效率

后端 SHALL use efficient caching for distance matrices and solution results, and SHALL avoid N+1 or unindexed database queries in scenario CRUD endpoints.

## REMOVED Requirements

无。
