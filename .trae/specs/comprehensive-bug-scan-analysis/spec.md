# 全面系统 BUG 扫描与分析 Spec

## Why

项目经历多轮重构后，需要一次全面、系统的质量体检，识别语法错误、逻辑缺陷、安全漏洞、依赖风险、测试缺口及运行时异常，形成可跟踪、可验证的 BUG 报告，为后续修复排期提供依据。

## What Changes

- **静态代码扫描**：对 Python（Ruff、Bandit、MyPy）和 TypeScript（ESLint、TypeScript 编译器）进行全量扫描，记录错误、警告与规范违规。
- **测试执行与失败分析**：运行后端 `pytest`、前端 `vitest` 及任何可用的端到端测试，收集失败用例与堆栈信息。
- **依赖安全审计**：使用 `pip-audit`/`safety` 扫描 Python 依赖，使用 `npm audit` 扫描前端依赖，记录 CVE 与兼容性问题。
- **关键模块手动测试**：对认证/限流、求解流程、场景 CRUD、文件上传、callback_url 校验等核心功能进行边界与异常场景测试。
- **日志与运行时异常分析**：检查现有日志文件、扫描 `console.error`/`stderr`，识别未处理异常模式。
- **报告生成**：汇总上述结果，输出 Markdown BUG 报告，包含问题描述、严重程度、复现步骤、影响范围与初步定位。

## Impact

- **受影响范围**：整个 Python 后端、React/TypeScript 前端、测试套件、依赖清单、CI 配置。
- **关键文件**：`reports/GreenVRP_Bug_Scan_Report.md`（待生成）、`pyproject.toml`、`web/package.json`、`tests/`、`api/`、`core/`、`web/src/`。

## ADDED Requirements

### Requirement: 全量静态扫描

The system SHALL be scanned by static analysis tools for both Python and TypeScript codebases.

#### Scenario: Python scan

- **WHEN** running `ruff check .`, `bandit -r .`, and `mypy .`
- **THEN** every violation is recorded with file path, line number, rule code, and severity

#### Scenario: TypeScript scan

- **WHEN** running `npm run lint` and `tsc -b` in `web/`
- **THEN** every error/warning is recorded with file path, line number, and message

### Requirement: 测试全量执行与失败记录

The system SHALL run all available tests and capture failures.

#### Scenario: Backend tests

- **WHEN** running `python -m pytest tests/ -v`
- **THEN** all failing tests, their error class, message, and traceback are captured

#### Scenario: Frontend tests

- **WHEN** running `npm run test -- --run` in `web/`
- **THEN** all failing tests, their error class, and message are captured

### Requirement: 依赖安全与兼容性审计

The system SHALL audit declared dependencies for known vulnerabilities and compatibility issues.

#### Scenario: Python dependencies

- **WHEN** running `pip-audit --format=json` or `python -m pip_audit`
- **THEN** every CVE, affected package, and fixed version is recorded

#### Scenario: Frontend dependencies

- **WHEN** running `npm audit --json`
- **THEN** every vulnerability, severity, and affected package is recorded

### Requirement: 关键功能手动边界测试

The system SHALL be manually exercised for boundary and error conditions in critical modules.

#### Scenario: API authentication edge cases

- **WHEN** calling protected endpoints with missing, wrong, empty, or malformed `GREENVRP_API_KEY`
- **THEN** behavior and HTTP status codes are recorded

#### Scenario: Solver boundary conditions

- **WHEN** submitting 0 customers, 1 customer, 1000+ customers, invalid coordinates, or malformed CSV
- **THEN** response behavior, errors, and status codes are recorded

### Requirement: 运行时异常与日志分析

The system SHALL scan for runtime error patterns in logs and stderr.

#### Scenario: Log scan

- **WHEN** examining `*.log`, `logs/`, `stderr`, and recent command outputs
- **THEN** unhandled exceptions, stack traces, and repeated warnings are catalogued

### Requirement: 生成 BUG 报告

The system SHALL produce a consolidated BUG report.

#### Scenario: Report generation

- **WHEN** all scans and tests complete
- **THEN** a Markdown report is written to `reports/GreenVRP_Bug_Scan_Report.md` with executive summary, issue tables, severity ratings, reproduction steps, impact, and initial root-cause locations

## MODIFIED Requirements

无。

## REMOVED Requirements

无。
