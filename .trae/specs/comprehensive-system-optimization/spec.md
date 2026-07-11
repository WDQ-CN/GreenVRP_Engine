# GreenVRP Engine 全面系统性优化 Spec

## Why

项目经过三期前端重构后，后端仍存在弱哈希（MD5）、API Key 未强制启用、代码规范与类型检查债务；前端生产包主 chunk 超过 500 KB；场景数据仍使用内存字典，重启后丢失。本次优化旨在消除安全与质量风险、提升运行性能与可维护性，并为后续功能扩展奠定坚实基础。

## What Changes

- **后端安全加固**：将缓存键中的 `hashlib.md5` 替换为 `hashlib.sha256`；API Key 认证默认“失败关闭”；为 FastAPI 增加请求体大小限制；统一异常响应脱敏；为 callback_url SSRF 校验补充单测。
- **后端代码质量**：集中修复 `api/`、`core/`、`utils/`、`config/`、`data_types/`、`optimization/`、`analysis/` 中的 Ruff 与 MyPy 问题；降低 Radon 识别的高复杂度函数。
- **后端性能优化**：重构距离矩阵缓存键生成逻辑；清理 `SolverPool` 中的无效池化代码；修复稀疏距离矩阵在 OR-Tools 路径中的兼容性问题。
- **数据持久化**：使用 SQLAlchemy + SQLite 持久化场景数据，替代内存字典，实现 API 重启后数据保留与更清晰的访问控制扩展点。
- **前端性能优化**：使用 `React.lazy + Suspense` 对页面路由做代码分割；在 `vite.config.ts` 中配置手动 chunk，使生产构建主 JS chunk < 500 KB。
- **前端体验增强**：增加全局加载与错误边界；优化 `TabsTrigger` 可访问性；统一网络/认证错误提示。
- **工程化与文档**：修复 CI 中 `ruff` 命令大小写问题；补充相关测试；更新 `ARCHITECTURE.md` 与 `CHANGELOG.md`。

## Impact

- **受影响功能**：API 认证与限流、求解缓存、距离/时间矩阵计算、场景管理、前端路由与构建、CI 流程。
- **关键文件**：`api/middleware/security.py`、`api/main.py`、`core/solver.py`、`core/distance.py`、`models/database.py`、`api/routers/scenarios.py`、`web/src/router/index.tsx`、`web/vite.config.ts`、`.github/workflows/ci.yml`。

## ADDED Requirements

### Requirement: 场景数据持久化

The system SHALL persist scenario CRUD operations to SQLite via SQLAlchemy instead of the in-memory dictionary.

#### Scenario: Create scenario

- **WHEN** user creates a scenario via `POST /api/v1/scenarios`
- **THEN** the scenario is stored in the database and survives an API server restart

#### Scenario: List scenarios after restart

- **WHEN** the API server restarts
- **THEN** `GET /api/v1/scenarios` returns previously saved scenarios

### Requirement: 生产构建主包体积控制

The system SHALL split frontend route chunks so that the production main JavaScript chunk is below 500 KB.

#### Scenario: Build

- **WHEN** running `npm run build` in the `web` directory
- **THEN** the largest initial JS chunk reported by Vite is smaller than 500 KB

### Requirement: API Key 默认拒绝访问

The system SHALL reject non-health requests with HTTP 401 when `GREENVRP_API_KEY` is unset, unless `GREENVRP_ALLOW_UNAUTHENTICATED=true` is explicitly set.

#### Scenario: Missing API key

- **WHEN** `GREENVRP_API_KEY` is not configured and `GREENVRP_ALLOW_UNAUTHENTICATED` is not `true`
- **THEN** `POST /api/v1/solve` returns 401

### Requirement: 请求体大小限制

The system SHALL limit the maximum request body size to prevent oversized payloads.

#### Scenario: Oversized payload

- **WHEN** a request body exceeds the configured limit
- **THEN** the API returns HTTP 413 without invoking the solver

## MODIFIED Requirements

### Requirement: 缓存键哈希算法

The system SHALL use `hashlib.sha256` (or equivalent) for all cache-key hashing and SHALL NOT use MD5 for any purpose.

#### Scenario: Distance matrix cache

- **WHEN** the distance matrix cache generates a key
- **THEN** it uses SHA-256, not MD5

#### Scenario: Solver solution cache

- **WHEN** the solver generates a solution cache key
- **THEN** it uses SHA-256, not MD5

### Requirement: 异常响应脱敏

The system SHALL return sanitized error messages for all unhandled exceptions and SHALL log detailed stack traces server-side only.

#### Scenario: Solver failure

- **WHEN** an unexpected error occurs in `/api/v1/solve`
- **THEN** the client receives a generic 500 message and the traceback is written to the server log

## REMOVED Requirements

### Requirement: 内存场景字典

**Reason**：由 SQLite 持久化替代，避免数据丢失并支持更细粒度的权限扩展。

**Migration**：开发/测试阶段的内存数据将在部署新代码后自然清空；生产环境通过数据库迁移保留数据。
