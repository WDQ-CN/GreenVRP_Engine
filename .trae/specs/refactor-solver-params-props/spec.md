# SolverParamsPanel + WorkspacePage Props 驱动重构 Spec

## Why

当前 `WorkspacePage` 通过 `useVehicleConfig` 同时获取车辆配置与求解参数，导致求解参数的数据流隐藏在通用 Hook 中，`SolverParamsPanel` 的输入/输出边界不够清晰。为了让 `SolverParamsPanel` 完全由 props 驱动、便于独立测试与复用，需要将求解参数状态从 `useVehicleConfig` 中剥离，并在 `WorkspacePage` 中显式管理。

## What Changes

- 新增 `useSolverParams` Hook，专门负责 `SolverParams` 的读取与局部更新。
- 调整 `useVehicleConfig`，不再返回 `params` / `setParams`。
- 更新 `WorkspacePage`，使用 `useSolverParams` 获取参数并透传给 `SolverParamsPanel`。
- 保持 `SolverParamsPanel` 纯 props 驱动：仅接收 `params` 与 `onParamsChange`，不直接访问 Store。
- 补充/更新 `useSolverParams`、`SolverParamsPanel`、`WorkspacePage` 相关单元测试。

## Impact

- **受影响功能**：求解工作台参数配置、车型配置。
- **关键文件**：
  - `web/src/hooks/useVehicleConfig.ts`
  - `web/src/hooks/useSolverParams.ts`（新增）
  - `web/src/pages/WorkspacePage.tsx`
  - `web/src/components/workspace/SolverParamsPanel.tsx`
  - `web/src/hooks/__tests__/useVehicleConfig.test.ts`
  - `web/src/hooks/__tests__/useSolverParams.test.ts`（新增）

## ADDED Requirements

### Requirement: 独立的求解参数 Hook

The system SHALL provide a `useSolverParams` hook that exposes `params` and `setParams`.

#### Scenario: 读取默认参数

- **WHEN** 组件调用 `useSolverParams()`
- **THEN** 返回与 Zustand Store 中一致的 `SolverParams`

#### Scenario: 局部更新参数

- **WHEN** 调用 `setParams({ fuel_price: 8.0 })`
- **THEN** Store 中 `params.fuel_price` 更新为 `8.0`，其余字段保持不变

### Requirement: 策略权重 Slider 交互测试覆盖

The system SHALL provide unit tests for the strategy weight slider interaction in `SolverParamsPanel`.

#### Scenario: 调整策略权重

- **WHEN** 用户在启用多策略后拖动某个策略权重 slider
- **THEN** `onParamsChange` 被调用，并传递更新后的 `strategy_weights` 对象，仅改变对应权重且其余权重保持不变

## MODIFIED Requirements

### Requirement: WorkspacePage 显式管理求解参数

`WorkspacePage` SHALL use `useSolverParams` for solver parameters and pass them to `SolverParamsPanel` via props.

#### Scenario: 参数变更

- **WHEN** 用户在 `SolverParamsPanel` 中修改参数
- **THEN** `WorkspacePage` 通过 `onParamsChange` 调用 `setParams`，更新后的参数回写到 Store

### Requirement: useVehicleConfig 职责单一化

`useVehicleConfig` SHALL only manage vehicle configuration and SHALL NOT expose `params` / `setParams`.

## REMOVED Requirements

无。
