# Checklist

- [x] `web/src/hooks/useSolverParams.ts` 已创建并通过单元测试
- [x] `useVehicleConfig.ts` 不再导出 `params` / `setParams`
- [x] `WorkspacePage.tsx` 使用 `useSolverParams` 并将参数透传至 `SolverParamsPanel`
- [x] `SolverParamsPanel.tsx` 内部不直接访问 Zustand Store，仅通过 props 驱动
- [x] 相关单元测试覆盖默认读取、局部更新、Hook 拆分后的行为
- [x] `SolverParamsPanel` 策略权重 slider 交互已覆盖单元测试
- [x] `npm run lint` 无新增报错
- [x] `npm run test -- --run` 全部通过
- [x] `npm run build` 构建成功
