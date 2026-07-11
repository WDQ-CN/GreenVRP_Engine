# GreenVRP Engine 分支策略

## 分支命名规范

| 分支类型 | 命名格式 | 示例 |
|:---------|:---------|:-----|
| **主分支** | `main` | `main` |
| **开发分支** | `develop` | `develop` |
| **功能分支** | `feature/<简短描述>` | `feature/tracking-module`, `feature/oauth2` |
| **修复分支** | `bugfix/<问题编号>-<描述>` | `bugfix/C-01-pydantic-crash` |
| **发布分支** | `release/v<版本号>` | `release/v2.1.0` |
| **热修复分支** | `hotfix/<严重问题描述>` | `hotfix/api-auth-bypass` |

## 工作流程

```
feature/*  ──┐
              ├──→  develop  ──→  release/v*  ──→  main (tag)
bugfix/*   ──┘                                      ↑
hotfix/*   ──────────────────────────────────────────┘
```

### 日常开发
1. 从 `main` 创建 `feature/<name>` 分支
2. 在 feature 分支上开发和测试
3. 提交 PR 到 `main`（需通过 CI + Code Review）
4. 合并后删除 feature 分支

### 发布流程
1. 从 `main` 创建 `release/v<version>` 分支
2. 在 release 分支上进行最终测试和文档更新
3. 合并回 `main` 并打版本标签 `v<version>`
4. 同步到 `develop`（如使用）

### 热修复
1. 从 `main` 创建 `hotfix/<description>` 分支
2. 修复并测试
3. 直接合并到 `main` 并打标签
4. 同步到其他活跃分支

## 版本号规范

遵循**语义化版本 2.0**：

```
vMAJOR.MINOR.PATCH
```

- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 向后兼容的功能新增
- **PATCH**: 向后兼容的 Bug 修复

当前版本：`v2.0.0`

## 提交信息规范

```
<type>: <简短描述>

<详细说明（可选）>
```

| type | 用途 |
|:-----|:------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `test` | 测试相关 |
| `refactor` | 代码重构 |
| `docs` | 文档更新 |
| `chore` | 构建/工具链 |
| `perf` | 性能优化 |
| `security` | 安全修复 |

### 示例
```
feat: 实现 GPS 位置追踪模块
fix: 修复 API 响应 Pydantic 校验崩溃 (C-01)
test: 为核心求解器添加单元测试
refactor: 提取 _setup_solver() 消除代码重复
```

## CI 门禁

所有 PR 合并前必须通过：
1. ✅ pytest 全部通过
2. ✅ 覆盖率不下降
3. ✅ flake8 无错误
4. ✅ pip-audit 无高危漏洞
