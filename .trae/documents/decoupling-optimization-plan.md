# GreenVRP Engine 解耦优化方案

## 一、方案概要

### 目标
对项目进行系统性解耦，使各模块能够**独立开发、测试和部署**，降低修改一个模块对其他模块的影响范围。

### 核心原则
1. **依赖倒置原则**：模块间依赖抽象而非具体实现
2. **单一职责原则**：每个模块只负责一个清晰的功能领域
3. **接口隔离原则**：模块间的交互契约小而专一
4. **测试友好**：解耦后可使用 Mock/Stub 替代真实依赖进行测试

### 实施路线
```
Phase A (已完服) → Phase B (已完成) → Phase C (已完成) → Phase D (完成 80%) → Phase E (未开始)
 服务层抽象        优化模块解耦        数据库抽象          前端组件解耦        前端API抽象
```

---

## 二、现状分析

### 2.1 已完成的工作

| 阶段 | 内容 | 涉及文件 |
|------|------|---------|
| **A1** | 创建 core/interfaces.py（ISolverService, IJobManager Protocol） | `core/interfaces.py` ✅ |
| **A2** | SolverService 类化，实现 ISolverService，构造函数支持 JobManager 注入 | `api/services/solver_service.py` ✅ |
| **A3** | API 路由使用 FastAPI Depends 注入 SolverService | `api/dependencies.py`, `api/routers/solver.py` ✅ |
| **B1-B2** | CarbonAwareOptimizer 改为接收 ISolverService 接口；移除反射检测 | `optimization/carbon_aware.py` ✅ |
| **C1-C2** | DatabaseProvider 类化，IDatabaseProvider 接口，保留向后兼容 | `models/interfaces.py`, `models/database.py` ✅ |
| **D1** | 创建 useCustomers、useSolver、useVehicleConfig 自定义 Hooks | `web/src/hooks/use*.ts` ✅ |
| **D2** | 创建 useSolveExecution、useSolveValidation Hooks；重构 WorkspacePage | `web/src/hooks/useSolve*.ts`, `WorkspacePage.tsx` ✅ |
| **D3** | SolverParamsPanel、VehicleConfigPanel、CustomerDataPanel 改为 props 驱动 + memo | 3 个 panel 文件 ✅ |

### 2.2 剩余问题

| ID | 问题 | 涉及文件 | 耦合类型 | 严重度 |
|----|------|---------|---------|--------|
| **R1** | ResultsPanel 仍使用 `useSolverStore()` 而非 props；customers 缺失 | `ResultsPanel.tsx` | 全局状态 | P0 |
| **R2** | VehicleConfigPanel 中 `removeVehicle` 调用 `setVehicleConfig`（不存在） | `VehicleConfigPanel.tsx:76` | Bug | P0 |
| **R3** | WorkspacePage 解构了 `clearError` 但未使用 | `WorkspacePage.tsx:41` | 编译警告 | P2 |
| **R4** | optimization/multi_objective.py 仍使用 `Callable` 而非 `ISolverService` | `multi_objective.py` | 隐式契约 | P2 |
| **R5** | `solver.ts` 直接 import `api` 实例，无法替换 HTTP 客户端 | `web/src/lib/solver.ts` | 实现依赖 | P2 |
| **R6** | 缺少 Hooks 和 Repository 的单元测试 | — | 测试覆盖 | P2 |
| **R7** | `solver_service.py` 末尾仍有全局实例（`solver_service = SolverService()`）| `solver_service.py:403` | 全局状态 | P3 |

### 2.3 已存在的良好实践（应保持）

- **analysis/ 模块**：ScenarioComparison 依赖纯数据输入，不依赖 core/ 模块 ✅
- **RouteMap**：纯展示组件，仅依赖 props ✅
- **CustomerTable**：纯展示组件，仅依赖 props ✅
- **FastAPI 的 Depends(get_db)**：已经使用依赖注入获取数据库会话 ✅
- **前端 Router**：已使用 React.lazy 延迟加载页面 ✅

---

## 三、详细实施方案

### Phase D3: ResultsPanel 改为 props 驱动

**涉及文件**:
- `web/src/components/workspace/ResultsPanel.tsx`
- `web/src/pages/WorkspacePage.tsx`

#### 变更内容

**ResultsPanel.tsx** (修改):

1. 移除 `useSolverStore` 导入（来自 `@/stores/solverStore`）
2. 在 `ResultsPanelProps` 中添加 `customers: Customer[]` 字段
3. 删除 `const { customers, currentSolution } = useSolverStore();`（第31行）
4. 将 `currentSolution` 所有引用替换为 `solution`（第34-35、45-46行）
5. 添加 `export const ResultsPanel = memo(ResultsPanelInner);`
6. 添加 `Customer` 类型导入（来自 `@/types`）

**WorkspacePage.tsx** (修改):

1. 从 `useCustomers()` 获取 `customers`
2. 将 `<ResultsPanel solution={currentSolution} />` 改为 `<ResultsPanel solution={currentSolution} customers={customers} />`
3. 将 `clearError` 改为 `_clearError` 或移除解构（仅保留 `loading, error, progress, handleSolve, handleCancel`）

**设计理由**:
- ResultsPanel 成为纯展示组件，不依赖全局 Store
- 与 D3 阶段其它 panel 保持一致的设计风格
- memo 在 props 不变时短路重渲染

---

### Phase D4: 修复 VehicleConfigPanel bug

**涉及文件**:
- `web/src/components/workspace/VehicleConfigPanel.tsx`

**变更内容**:
- 第76行：`setVehicleConfig(vehicleConfig.filter(...))` → `onConfigChange(vehicleConfig.filter(...))`

**设计理由**:
- 这是一个在 D3 重构中引入的 Bug：`setVehicleConfig` 已在 props 中重命名为 `onConfigChange`
- 当前代码会导致运行时 `setVehicleConfig is not a function` 错误

---

### Phase E: 前端 API 抽象层

#### E1. 创建 Repository 接口

**新建文件**: `web/src/lib/repositories/interfaces.ts`

```typescript
import type { SolveRequest, SolveResponse } from '@/types';

export interface ISolverRepository {
  solveSync(request: SolveRequest): Promise<SolveResponse>;
  solveAsync(request: SolveRequest): Promise<{ job_id: string; status: string; message: string }>;
  getJobStatus(jobId: string): Promise<SolveResponse>;
}

export interface IJobStatusRepository {
  pollJobStatus(
    jobId: string,
    options?: { intervalMs?: number; maxAttempts?: number; onProgress?: (res: SolveResponse) => void; signal?: AbortSignal }
  ): Promise<SolveResponse>;
}
```

**设计理由**:
- Repository 模式是标准的企业级数据访问模式
- 接口即契约，将 HTTP 客户端与业务逻辑分离
- 测试时可替换为 MockSolverRepository

#### E2. 实现 HttpSolverRepository

**新建文件**: `web/src/lib/repositories/solverRepository.ts`

将 `solver.ts` 中的 `solveSync`, `solveAsync`, `getJobStatus`, `pollJobStatus` 移到 `HttpSolverRepository` 类中：

```typescript
import axios from 'axios';
import type { ISolverRepository, IJobStatusRepository } from './interfaces';
import type { SolveRequest, SolveResponse } from '@/types';
import { api } from '@/lib/api';
import { buildVehicleConfigMap, buildSolverParams, normalizeCustomers } from '@/lib/solver';

export class HttpSolverRepository implements ISolverRepository {
  async solveSync(request: SolveRequest): Promise<SolveResponse> {
    const payload = {
      customers: normalizeCustomers(request.customers),
      vehicle_config: request.vehicle_config ?? 
        (request.vehicleConfig ? buildVehicleConfigMap(request.vehicleConfig as any) : undefined),
      params: request.params ?? 
        (request.solverParams ? buildSolverParams(request.solverParams as any) : undefined),
    };
    const { data } = await api.post<SolveResponse>('/solve', payload);
    return data;
  }

  async solveAsync(request: SolveRequest): Promise<{ job_id: string; status: string; message: string }> {
    const payload = { /* same as above, plus callback_url */ };
    const { data } = await api.post('/solve/async', payload);
    return data;
  }

  async getJobStatus(jobId: string): Promise<SolveResponse> {
    const { data } = await api.get<SolveResponse>(`/jobs/${jobId}`);
    return data;
  }
}

export class HttpJobStatusRepository implements IJobStatusRepository {
  constructor(private baseRepo: ISolverRepository) {}

  async pollJobStatus(
    jobId: string,
    options: { intervalMs?: number; maxAttempts?: number; onProgress?: (res: SolveResponse) => void; signal?: AbortSignal } = {}
  ): Promise<SolveResponse> {
    const { intervalMs = 1500, maxAttempts = 120, onProgress, signal } = options;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      if (signal?.aborted) throw new Error('求解任务已取消');
      const response = await this.baseRepo.getJobStatus(jobId);
      onProgress?.(response);
      if (response.status === 'completed') return response;
      if (response.status === 'failed') throw new Error(response.error_message || response.error || '求解任务执行失败');
      await new Promise<void>((resolve) => {
        const timer = setTimeout(resolve, intervalMs);
        signal?.addEventListener('abort', () => clearTimeout(timer), { once: true });
      });
    }
    throw new Error('求解任务轮询超时');
  }
}
```

#### E3. 重构 lib/solver.ts

**修改文件**: `web/src/lib/solver.ts`

`buildVehicleConfigMap`, `buildSolverParams`, `normalizeCustomers` 保留为纯工具函数（它们不依赖 api）。
`solveSync`, `solveAsync`, `getJobStatus`, `pollJobStatus` 改为委托到 Repository 实例：

```typescript
import { HttpSolverRepository, HttpJobStatusRepository } from './repositories/solverRepository';
import type { ISolverRepository } from './repositories/interfaces';

let repository: ISolverRepository | null = null;

export function setSolverRepository(repo: ISolverRepository) {
  repository = repo;
}

function getRepository(): ISolverRepository {
  if (!repository) {
    repository = new HttpSolverRepository();
  }
  return repository;
}

// 导出纯工具函数（不变）
export function buildVehicleConfigMap(...) { ... }
export function buildSolverParams(...) { ... }
export function normalizeCustomers(...) { ... }

// 委托到 Repository
export async function solveSync(...) {
  return getRepository().solveSync({ customers, ... });
}

export async function solveAsync(...) {
  return getRepository().solveAsync({ customers, ... });
}

export async function getJobStatus(jobId: string) {
  return getRepository().getJobStatus(jobId);
}

export async function pollJobStatus(jobId: string, options?) {
  const statusRepo = new HttpJobStatusRepository(getRepository());
  return statusRepo.pollJobStatus(jobId, options);
}
```

**设计理由**:
- `setSolverRepository` 提供工厂替换能力，测试时注入 Mock
- 纯工具函数保持不变，不影响已有测试
- 向后兼容：`solver.ts` 导出签名不变，调用方无需修改

---

### Phase V: 测试验证

#### V1. 为 Hooks 添加单元测试

**新建文件**: `web/src/hooks/__tests__/useCustomers.test.ts`
**新建文件**: `web/src/hooks/__tests__/useSolveValidation.test.ts`
**新建文件**: `web/src/hooks/__tests__/useVehicleConfig.test.ts`

测试策略：
- `useCustomers` / `useVehicleConfig`：验证 Selector 返回值正确、计算属性准确
- `useSolveValidation`：验证正确检测缺少仓库、客户不足等情形

#### V2. 为 Repository 添加单元测试

**新建文件**: `web/src/lib/repositories/__tests__/solverRepository.test.ts`

测试策略：
- 创建 `MockSolverRepository` 实现 `ISolverRepository`
- 验证 `HttpSolverRepository.solveSync` 正确构建 payload
- 验证 `pollJobStatus` 的轮询逻辑

#### V3. 回归测试

```bash
# 前端
cd web && npm run test -- --run  # 现有 3 个测试 + 新增测试
cd web && npm run lint            # 检查 lint
cd web && npm run build           # 验证构建

# 后端
pytest tests/                     # 运行后端测试
```

---

## 四、实施顺序与工作量

| 任务 | 文件 | 类型 | 风险 |
|------|------|------|------|
| **D3** ResultsPanel props 化 | `ResultsPanel.tsx`, `WorkspacePage.tsx` | 修改 | 低 |
| **D4** VehicleConfigPanel 修复 | `VehicleConfigPanel.tsx` | 修改 | 低 |
| **E1** Repository 接口 | `repositories/interfaces.ts` | 新建 | 低 |
| **E2** HTTP Repository | `repositories/solverRepository.ts` | 新建 | 低 |
| **E3** 重构 solver.ts | `solver.ts` | 修改 | 中（需确保向后兼容） |
| **V1** Hooks 单元测试 | 3 个测试文件 | 新建 | 低 |
| **V2** Repository 测试 | 1 个测试文件 | 新建 | 低 |
| **V3** 回归测试验证 | 运行测试 | 验证 | — |

---

## 五、验收标准

| 标准 | 验收方式 | 预期结果 |
|------|---------|---------|
| ResultsPanel 不直接使用 Store | 代码审查 | `useSolverStore` 从 import 中移除 |
| VehicleConfigPanel 删除按钮正常工作 | 功能测试 | 点击删除按钮移除车型 |
| Repository 可切换实现 | 单元测试 | `setSolverRepository(mockRepo)` 后 API 调用走 Mock |
| 所有现有测试通过 | CI | `npm run test` 全部通过 |
| 构建通过 | CI | `npm run build` 无错误 |
| Lint 通过 | CI | `npm run lint` 无 error |
