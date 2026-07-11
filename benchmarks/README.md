# 性能基准测试体系

本目录包含 GreenVRP Engine 的前端、API、后端性能基准与分析脚本，用于建立可重复的性能基线并验证优化效果。

## 目录结构

```
benchmarks/
├── frontend/
│   └── lighthouse.mjs       # Lighthouse 前端性能测试
├── api/
│   └── benchmark_api.py     # API 端点压力测试
├── backend/
│   └── profile_solver.py    # 求解器/距离矩阵 cProfile 分析
└── README.md                # 本说明
```

## 关键指标与目标

| 指标 | 测试脚本 | 当前基线 | 目标 |
|------|---------|---------|------|
| Lighthouse Performance | `frontend/lighthouse.mjs` | 91 | ≥ 80 或较基线提升 20% |
| 首屏 LCP | `frontend/lighthouse.mjs` | 2811.78 ms | ≤ 2249.42 ms（基线 80%） |
| `/api/v1/solve` P95 | `api/benchmark_api.py` | 5017.58 ms | ≤ 4014.06 ms（基线 80%） |
| `/api/v1/scenarios` P95 | `api/benchmark_api.py` | 6.95 ms | ≤ 5.56 ms（基线 80%） |
| 距离矩阵 1000 点 CPU 耗时 | `backend/profile_solver.py` | 3469.39 ms | ≤ 2775.51 ms（基线 80%） |
| 求解器 20 点 CPU 耗时 | `backend/profile_solver.py` | 10052.49 ms | ≤ 8041.99 ms（基线 80%） |

## 运行方式

### 前端基准

```bash
cd web
npm install   # 首次需要安装 lighthosue / chrome-launcher
npm run build
node ../benchmarks/frontend/lighthouse.mjs
```

### API 基准

```bash
python benchmarks/api/benchmark_api.py
```

### 后端分析

```bash
python benchmarks/backend/profile_solver.py
```

## 输出

- 前端：`benchmarks/frontend/results/lighthouse.json`
- API：`benchmarks/api/results/api_benchmark.json`
- 后端：`benchmarks/backend/results/backend_profile.json`

所有结果 JSON 均会随每次运行覆盖，用于优化前后的对比。
