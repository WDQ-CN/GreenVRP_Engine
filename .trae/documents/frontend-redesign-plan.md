# GreenVRP Engine 前端重构与视觉设计方案

## 1. 项目目标与范围

### 1.1 目标

将现有基于 Streamlit 的 GreenVRP Engine 前端（`web_app.py`、`frontend/app.py`）重构为现代 React 单页应用（SPA），采用企业级 SaaS 视觉风格，提升：

- **专业感与品牌一致性**：中性蓝灰主色，清晰的信息层级
- **交互效率**：表单校验、异步反馈、键盘导航、批量操作
- **可维护性**：组件化、类型安全、自动化测试
- **性能**：代码分割、懒加载、数据缓存
- **可扩展性**：支持未来多租户、角色权限、主题切换

### 1.2 范围

- **包含**：
  - 登录/设置 API Key 入口
  - 主布局（侧边栏 + 顶部栏 + 内容区）
  - 参数配置面板（经济参数、车型配置）
  - 客户数据管理（表格编辑、CSV 导入、示例数据加载）
  - 求解控制台（同步/异步求解、任务状态）
  - 结果可视化（地图、路线列表、车辆使用、成本分析）
  - 多方案对比
  - 场景管理
- **不包含**：
  - 后端业务逻辑改造（后端 API 保持独立）
  - 复杂的权限 RBAC（一期仅 API Key 认证）

---

## 2. 现状分析

当前 Streamlit 版本已实现以下功能模块：

| 模块 | 位置 | 说明 |
|------|------|------|
| 参数配置 | `web_app.py` 侧边栏 | 油价、时薪、碳价、迟到罚金、求解时间、多策略开关 |
| 车型配置 | `web_app.py` 侧边栏 | 4.2m / 7.6m / 9.6m 车辆数量、载重、固定成本、油耗、速度、颜色 |
| 客户数据 | `web_app.py` 主面板 | CSV 上传、示例数据、客户表格 |
| 地图展示 | `web_app.py` | 客户/路线在地图上的可视化 |
| 成本分析 | `web_app.py` | 成本构成、关键指标、成本明细 |
| 路线详情 | `web_app.py` | 每辆车的停靠点列表 |
| 车辆使用 | `web_app.py` | 车辆使用柱状图/饼图 |
| 多方案对比 | `web_app.py` | 多种求解策略对比、最佳方案加载 |
| 企业版 UI | `frontend/app.py` | Dashboard、企业风格标题、状态标签 |

后端 API 端点（FastAPI）：

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/scenarios` | CRUD | 场景管理 |
| `/api/v1/solve` | POST | 同步求解 |
| `/api/v1/solve/async` | POST | 异步求解 |
| `/api/v1/jobs/{id}` | GET | 任务状态 |
| `/api/v1/jobs` | GET | 任务列表 |

---

## 3. 技术栈选型

| 层级 | 技术 | 理由 |
|------|------|------|
| 框架 | **React 19 + TypeScript** | 类型安全、生态成熟、企业级首选 |
| 构建工具 | **Vite 6** | 快速 HMR、Tree Shaking、配置简洁 |
| 路由 | **React Router v7** | 声明式路由、懒加载、数据加载器 |
| UI 组件库 | **shadcn/ui** | 基于 Tailwind、可定制、无运行时依赖、企业风组件丰富 |
| 样式 | **Tailwind CSS 4** | 原子化、设计 token 一致、响应式友好 |
| 图标 | **Lucide React** | 简洁线性图标，适合 SaaS |
| 地图 | **MapLibre GL JS + react-map-gl** | 开源、无需 Token、支持自定义样式 |
| 图表 | **Recharts** | React 原生、配置灵活、满足成本/车辆图表 |
| 表格 | **TanStack Table v8** | 排序、筛选、分页、虚拟化 |
| 数据请求 | **TanStack Query v5** | 缓存、重试、轮询、乐观更新 |
| 状态管理 | **Zustand** | 轻量、TypeScript 友好，用于全局 UI/求解状态 |
| 表单 | **React Hook Form + Zod** | 性能优、校验强，与 shadcn Form 集成好 |
| HTTP 客户端 | **Axios** | 拦截器、请求取消、上传进度 |
| 测试 | **Vitest + React Testing Library** | 与 Vite 集成、测试体验好 |

---

## 4. 设计系统

### 4.1 色彩体系

以 **Slate + Blue** 为主，绿色作为品牌强调色呼应 GreenVRP 主题。

```
Primary:     #0F172A  (slate-900)    主标题、关键文字、顶部栏背景
Primary-2:   #1E293B  (slate-800)    卡片标题、次要背景
Accent:      #2563EB  (blue-600)     主按钮、链接、选中状态
Accent-Hover:#1D4ED8  (blue-700)
Success:     #16A34A  (green-600)    成功、低碳指标
Warning:     #D97706  (amber-600)    警告、迟到/超时
Danger:      #DC2626  (red-600)      错误、删除
Info:        #0891B2  (cyan-600)     提示信息
Background:  #F8FAFC  (slate-50)     页面背景
Surface:     #FFFFFF  (white)        卡片、面板背景
Border:      #E2E8F0  (slate-200)    边框、分割线
Text-Main:   #0F172A  (slate-900)
Text-Second: #64748B  (slate-500)
Text-Muted:  #94A3B8  (slate-400)
```

### 4.2 字体

- **中文**：系统无衬线字体栈 `"PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif`
- **英文/数字**：`Inter, -apple-system, BlinkMacSystemFont, sans-serif`
- **代码/数值**：`"SF Mono", "Fira Code", monospace`

### 4.3 间距与圆角

- 基础间距：`4px` 栅格，常用 `4 / 8 / 12 / 16 / 24 / 32 / 48`
- 卡片内边距：`p-6`（24px）
- 卡片圆角：`rounded-xl`（12px）
- 按钮圆角：`rounded-lg`（8px）
- 输入框圆角：`rounded-md`（6px）
- 阴影：`shadow-sm`（输入框）、`shadow-md`（卡片）、`shadow-lg`（弹窗/下拉）

### 4.4 布局网格

- 侧边栏宽度：`280px`（桌面），移动端抽屉
- 顶部栏高度：`64px`
- 内容区最大宽度：`1440px`，居中对齐
- 响应式断点：sm 640 / md 768 / lg 1024 / xl 1280 / 2xl 1536

---

## 5. 信息架构与路由

```
/                         → 工作台（Dashboard）
/workspace                → 求解工作台（参数、客户、求解、结果）
/workspace/scenarios      → 场景管理
/workspace/comparison     → 多方案对比
/analytics                → 成本分析
/analytics/cost           → 成本构成与明细
/analytics/routes         → 路线详情
/analytics/vehicles       → 车辆使用
/settings                 → 设置（API Key、主题、语言）
```

### 5.1 主导航结构

| 分组 | 菜单项 | 图标 | 路由 |
|------|--------|------|------|
| 核心 | 工作台 | LayoutDashboard | / |
| 核心 | 求解工作台 | Truck | /workspace |
| 核心 | 场景管理 | FolderOpen | /workspace/scenarios |
| 分析 | 成本分析 | BarChart3 | /analytics/cost |
| 分析 | 路线详情 | Map | /analytics/routes |
| 分析 | 车辆使用 | PieChart | /analytics/vehicles |
| 分析 | 方案对比 | GitCompare | /workspace/comparison |
| 系统 | 设置 | Settings | /settings |

---

## 6. 组件架构

### 6.1 原子组件（基于 shadcn/ui 扩展）

- `Button`：Primary / Secondary / Ghost / Danger，支持 loading 状态
- `Input` / `NumberInput` / `Slider`：统一聚焦态、错误态
- `Select` / `Combobox`：车型选择、策略选择
- `Card` / `CardHeader` / `CardContent`：信息卡片
- `Badge`：状态标签（成功、处理中、失败、等待中）
- `Tabs`：内容分区
- `Table` / `DataTable`：客户列表、路线列表
- `Dialog` / `Drawer`：导入确认、任务详情
- `Toast`：操作反馈
- `Skeleton`：加载占位

### 6.2 业务组件

| 组件 | 职责 |
|------|------|
| `AppShell` | 顶部栏 + 侧边栏 + 内容区布局 |
| `AuthGuard` | API Key 校验与输入弹窗 |
| `SolverParamsForm` | 经济参数、求解器参数表单 |
| `VehicleConfigEditor` | 车型配置卡片组 |
| `CustomerDataTable` | 客户数据增删改 + CSV 导入 |
| `CustomerMap` | 地图展示客户与路线 |
| `SolveControlPanel` | 求解按钮、同步/异步切换、状态显示 |
| `JobStatusList` | 异步任务列表与轮询 |
| `CostAnalysisCards` | 总成本、碳排放、里程、车辆数 |
| `CostBreakdownChart` | 成本构成堆叠柱状图/饼图 |
| `RouteTimeline` | 每辆车路线时间轴 |
| `VehicleUsageChart` | 车辆使用柱状图 |
| `StrategyComparisonTable` | 多方案对比表格 |
| `ScenarioManager` | 场景 CRUD |

### 6.3 页面组件

- `DashboardPage`：关键指标、最近任务、快捷入口
- `WorkspacePage`：参数 + 客户 + 求解 + 结果（标签页）
- `ScenariosPage`：场景列表、导入导出
- `ComparisonPage`：多策略对比
- `CostAnalysisPage`：成本相关图表
- `RoutesPage`：路线地图与列表
- `VehiclesPage`：车辆使用分析
- `SettingsPage`：API Key、主题、关于

---

## 7. API 集成方案

### 7.1 Axios 封装

```ts
// lib/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const key = localStorage.getItem('greenvrp_api_key');
  if (key) config.headers['X-API-Key'] = key;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      // 触发全局认证弹窗
      window.dispatchEvent(new CustomEvent('greenvrp:unauthorized'));
    }
    return Promise.reject(err);
  }
);

export default api;
```

### 7.2 TanStack Query Hooks

```ts
// hooks/useSolve.ts
import { useMutation, useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import type { SolveRequest, SolveResponse, JobStatus } from '@/types';

export const useSolveSync = () =>
  useMutation({
    mutationFn: (payload: SolveRequest) =>
      api.post<SolveResponse>('/solve', payload).then((r) => r.data),
  });

export const useSolveAsync = () =>
  useMutation({
    mutationFn: (payload: SolveRequest) =>
      api.post<{ job_id: string }>('/solve/async', payload).then((r) => r.data),
  });

export const useJobStatus = (jobId: string | null) =>
  useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.get<JobStatus>(`/jobs/${jobId}`).then((r) => r.data),
    enabled: !!jobId,
    refetchInterval: (q) => (q.state.data?.status === 'pending' ? 2000 : false),
  });
```

---

## 8. 状态管理

### 8.1 Zustand Store

```ts
// stores/solverStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { SolveRequest, SolveResponse } from '@/types';

interface SolverState {
  params: SolveRequest['params'];
  vehicleConfig: SolveRequest['vehicle_config'];
  customers: SolveRequest['customers'];
  currentSolution: SolveResponse | null;
  comparisonResults: SolveResponse[];
  setParams: (p: Partial<SolverState['params']>) => void;
  setVehicleConfig: (v: SolverState['vehicleConfig']) => void;
  setCustomers: (c: SolverState['customers']) => void;
  setCurrentSolution: (s: SolveResponse | null) => void;
  addComparisonResult: (s: SolveResponse) => void;
}

export const useSolverStore = create<SolverState>()(
  persist(
    (set) => ({
      params: {
        fuel_price: 7.5,
        hourly_wage: 50,
        carbon_price: 0.08,
        late_penalty_per_min: 10,
        search_time_limit: 30,
        use_multi_strategy: true,
        use_parallel: true,
      },
      vehicleConfig: DEFAULT_VEHICLE_CONFIG,
      customers: [],
      currentSolution: null,
      comparisonResults: [],
      setParams: (p) => set((state) => ({ params: { ...state.params, ...p } })),
      setVehicleConfig: (v) => set({ vehicleConfig: v }),
      setCustomers: (c) => set({ customers: c }),
      setCurrentSolution: (s) => set({ currentSolution: s }),
      addComparisonResult: (s) =>
        set((state) => ({ comparisonResults: [...state.comparisonResults, s] })),
    }),
    { name: 'greenvrp-solver-storage' }
  )
);
```

---

## 9. 性能优化策略

- **代码分割**：按路由懒加载页面组件
- **数据缓存**：TanStack Query 缓存求解结果与场景列表
- **虚拟化**：客户列表、路线列表使用虚拟滚动（>100 行时）
- **防抖**：参数输入使用 300ms 防抖写入 URL query / store
- **地图优化**：聚合点（cluster）处理大量客户；路线只渲染当前选中车辆
- **图表懒加载**：进入视口再渲染复杂图表
- **资源优化**：图标按需导入、字体子集化

---

## 10. 可访问性（a11y）

- 所有按钮/链接支持键盘导航
- 表单元素关联 `label` 与 `aria-describedby`
- 颜色对比度符合 WCAG 2.1 AA
- 加载状态使用 `aria-busy` 与 `aria-live`
- 弹窗使用 `aria-modal` 与焦点陷阱

---

## 11. 实现路线图

### Phase 1：基础搭建（1-2 天）

1. 初始化 Vite + React + TypeScript 项目
2. 配置 Tailwind CSS、shadcn/ui、React Router
3. 配置 ESLint、Prettier、Vitest
4. 搭建 `AppShell`、基础路由、暗黑/浅色主题切换
5. 实现 `AuthGuard` 与 API Key 输入弹窗

### Phase 2：核心工作台（3-4 天）

1. `SolverParamsForm` 参数配置表单
2. `VehicleConfigEditor` 车型配置
3. `CustomerDataTable` + CSV 导入
4. `SolveControlPanel` 求解控制
5. 求解结果展示（地图、路线、车辆使用）
6. 集成 TanStack Query 与 Zustand

### Phase 3：分析与管理（2-3 天）

1. 成本分析页面（Recharts 图表）
2. 多方案对比页面
3. 场景管理页面
4. 异步任务列表与轮询

### Phase 4：打磨与部署（2 天）

1. 响应式适配
2. 加载状态与空状态
3. Vitest 单元测试覆盖核心组件
4. 构建 Docker 镜像或静态站点部署
5. 与后端联调

---

## 12. 核心示例代码

### 12.1 主布局 AppShell

```tsx
// components/layout/AppShell.tsx
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { Outlet } from 'react-router-dom';

export function AppShell() {
  return (
    <div className="flex h-screen bg-slate-50 text-slate-900">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-auto p-6">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
```

### 12.2 工作台页面

```tsx
// pages/WorkspacePage.tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SolverParamsForm } from '@/components/solver/SolverParamsForm';
import { VehicleConfigEditor } from '@/components/solver/VehicleConfigEditor';
import { CustomerDataTable } from '@/components/customer/CustomerDataTable';
import { SolveControlPanel } from '@/components/solver/SolveControlPanel';
import { ResultDashboard } from '@/components/result/ResultDashboard';

export function WorkspacePage() {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      <aside className="space-y-6 lg:col-span-3">
        <SolverParamsForm />
        <VehicleConfigEditor />
        <SolveControlPanel />
      </aside>

      <section className="lg:col-span-9">
        <Tabs defaultValue="customers">
          <TabsList className="mb-4">
            <TabsTrigger value="customers">客户数据</TabsTrigger>
            <TabsTrigger value="results">求解结果</TabsTrigger>
          </TabsList>
          <TabsContent value="customers">
            <CustomerDataTable />
          </TabsContent>
          <TabsContent value="results">
            <ResultDashboard />
          </TabsContent>
        </Tabs>
      </section>
    </div>
  );
}
```

### 12.3 成本分析卡片

```tsx
// components/analytics/CostAnalysisCards.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatCO2 } from '@/lib/format';
import type { CostResult } from '@/types';

interface Props {
  costResult: CostResult;
}

export function CostAnalysisCards({ costResult }: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-500">总成本</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatCurrency(costResult.total_cost)}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-500">碳排放</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-green-600">{formatCO2(costResult.total_co2)}</div>
        </CardContent>
      </Card>
      {/* 更多指标卡片... */}
    </div>
  );
}
```

---

## 13. 风险与建议

- **地图 Token**：MapLibre 可完全免费使用；若需高清卫星图可考虑 MapTiler。
- **求解超时**：同步求解设置默认 30 秒超时，UI 需明确提示并引导异步求解。
- **API Key 安全**：前端存储 API Key 于 `localStorage` 存在 XSS 风险；后续如需更高安全性，应引入后端会话/OAuth2。
- **文件大小**：CSV 导入限制 5MB，大文件建议后端批量处理。
