# Checklist

- [ ] `benchmarks/` 目录包含前端、API、后端三类可重复运行的基准/分析脚本
- [ ] 基线指标已采集并记录（Lighthouse、Web Vitals、API P50/P95/P99、求解器热点耗时）
- [ ] 前端性能瓶颈已识别并实施至少一项有效优化（重依赖拆分、资源压缩、渲染优化等）
- [ ] 后端性能瓶颈已识别并实施至少一项有效优化（查询优化、缓存提升、求解器路径优化等）
- [ ] 前端 Lighthouse Performance 评分 ≥ 80 或较基线提升 20%
- [ ] 首屏 LCP 控制在基线的 80% 以内
- [ ] `/api/v1/solve` 同步模式 P95 响应时间控制在基线的 80% 以内
- [ ] `/api/v1/scenarios` 列表查询 P95 响应时间控制在基线的 80% 以内
- [ ] 求解器 CPU 耗时（相同数据集）控制在基线的 80% 以内
- [ ] `pytest tests/` 与 `npm run test -- --run` 全部通过（无回归）
- [ ] `reports/Performance_Optimization_Report.md` 已生成并包含完整优化记录
- [ ] 最终 `ruff`、`npm run lint`、`npm run build` 均通过
