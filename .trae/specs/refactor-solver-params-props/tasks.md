# Tasks

- [x] Task 1：提取 `useSolverParams` Hook
  - [x] SubTask 1.1：创建 `web/src/hooks/useSolverParams.ts`，从 Zustand Store 读取 `params` / `setParams`
  - [x] SubTask 1.2：为 `setParams` 包裹 `useCallback`，保持引用稳定
  - [x] SubTask 1.3：创建 `web/src/hooks/__tests__/useSolverParams.test.ts`，覆盖默认读取与局部更新

- [x] Task 2：精简 `useVehicleConfig`
  - [x] SubTask 2.1：从 `useVehicleConfig.ts` 中移除 `params`、`setParams` 导出
  - [x] SubTask 2.2：更新 `useVehicleConfig.test.ts`，移除与 params 相关的断言

- [x] Task 3：更新 `WorkspacePage`
  - [x] SubTask 3.1：在 `WorkspacePage.tsx` 中引入并使用 `useSolverParams`
  - [x] SubTask 3.2：将 `params` / `setParams` 透传给 `SolverParamsPanel`
  - [x] SubTask 3.3：保留 `vehicleConfig` / `setVehicleConfig` 使用 `useVehicleConfig`

- [x] Task 4：验证 `SolverParamsPanel` 纯 props 驱动
  - [x] SubTask 4.1：确认组件内部无 Store/Hook 调用
  - [x] SubTask 4.2：确认 `onParamsChange` 仅传递 `Partial<SolverParams>`

- [x] Task 5：工程化验证
  - [x] SubTask 5.1：运行 `npm run lint` 无新增报错
  - [x] SubTask 5.2：运行 `npm run test -- --run` 全部通过
  - [x] SubTask 5.3：运行 `npm run build` 构建成功

- [x] Task 6：补充策略权重 slider 交互测试
  - [x] SubTask 6.1：在 `SolverParamsPanel.test.tsx` 中增加 slider 交互测试，覆盖权重拖动后 `onParamsChange` 被调用且仅更新对应权重
  - [x] SubTask 6.2：运行 `npm run test -- --run` 全部通过
  - [x] SubTask 6.3：运行 `npm run lint` 无新增报错
  - [x] SubTask 6.4：运行 `npm run build` 构建成功

# Task Dependencies

- Task 2 依赖 Task 1
- Task 3 依赖 Task 1 与 Task 2
- Task 4 可与 Task 3 并行
- Task 5 依赖 Task 1 ~ Task 4
- Task 6 依赖 Task 4
