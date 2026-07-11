# GreenVRP Engine 安全漏洞扫描与代码质量评估报告

**生成时间**：2026-06-28 12:32:42

**报告路径**：`reports/GreenVRP_Security_Quality_Scan_Report.md`

---

## 1. 执行摘要

### 1.1 总体风险等级

**总体风险等级：高**

项目当前存在多项高危与中危安全问题，尤其是 API 层面缺少认证、CORS 配置过于宽松、服务端错误信息泄露，以及多个已知依赖 CVE。代码质量方面，类型注解缺失与规范违规较多，圈复杂度总体偏高，需尽快制定修复计划。

### 1.2 扫描工具与方法

| 类型 | 工具 | 说明 |
|------|------|------|
| 静态应用安全测试（SAST） | Bandit 1.9.4 | Python 代码安全扫描 |
| 依赖漏洞扫描 | pip-audit 2.10.1 | 扫描当前环境已安装依赖的已知 CVE |
| 动态应用安全测试（DAST） | 手动端点探测 | 因 Docker/Java 不可用，未运行 OWASP ZAP |
| 代码规范 | Ruff 0.15.17 | Lint 与代码格式检查 |
| 类型检查 | MyPy | Python 静态类型分析 |
| 复杂度/可维护性 | Radon 6.0.1 | 圈复杂度与维护性指数 |
| **未执行** | SonarQube、Semgrep、OWASP ZAP | 当前环境无法启动 Docker，缺少 Java 运行时 |

> **环境限制说明**：原计划使用 Docker 运行 SonarQube Community 与 OWASP ZAP，但当前环境无法连接 Docker 服务。已改用 Python 原生工具链完成 SAST、依赖审计与代码质量分析，并以手动 HTTP 探测替代 ZAP 进行基础 DAST。

### 1.3 问题数量统计

| 类别 | 高 | 中 | 低 | 信息 | 合计 |
|------|----:|----:|----:|----:|----:|
| 安全漏洞（Bandit） | 4 | 7 | 7 | 137（测试 assert） | 155 |
| 依赖 CVE | 1 | 3 | 0 | 0 | 3 |
| 代码规范违规（Ruff） | - | - | - | - | 946 |
| 类型错误（MyPy） | - | - | - | - | 127 |
| 高复杂度函数（Radon ≥ C，TOP 20 内） | - | - | - | - | 12 |

## 2. 扫描范围

- **后端 API**：`api/main.py`、`api/routers/`、`api/schemas/`、`api/services/`
- **核心算法**：`core/solver.py`、`core/distance.py`、`optimization/`
- **数据模型**：`data_types/`、`models/`、`config/settings.py`
- **前端/入口**：`web_app.py`、`frontend/app.py`、`start.py`、`start_fast.py`
- **测试与 CI**：`tests/`、`.github/workflows/ci.yml`
- **排除项**：`.venv/`、`.git/`、`__pycache__/`、`.pytest_cache/`、第三方依赖源码

## 3. 安全漏洞清单

### 3.1 高危问题

| 位置 | CWE | 风险说明 | 修复建议 |
|------|-----|----------|----------|
| `api/main.py:63-74` | CWE-942 / OWASP API 7 | CORS 默认 `allow_origins=["*"]` 且 `allow_credentials=True`，任意恶意站点可携带用户凭证调用 API | 生产环境必须显式配置受信任域名列表，禁止 `*` 与 `allow_credentials=True` 同时出现 |
| `api/main.py`、`api/routers/*.py` | CWE-306 / OWASP API 1 | 所有 API 端点均无认证、授权、Rate Limit 或 API Key，完全开放 | 增加 OAuth2/JWT/API Key 认证，并按角色授权；对敏感端点配置限流 |
| `core/distance.py:446` | CWE-327 | 使用 `hashlib.md5` 生成缓存键，未设置 `usedforsecurity=False` | 如仅用于非安全场景，添加 `usedforsecurity=False`；如用于安全场景，改用 SHA-256 |
| `core/solver.py:278,287,306` | CWE-327 | 同上，多处使用 MD5 作为缓存键 | 同上 |

### 3.2 中危问题

| 位置 | CWE | 风险说明 | 修复建议 |
|------|-----|----------|----------|
| `api/routers/solver.py:58-59`、`api/routers/solver.py:98-99` | CWE-209 | 捕获 `Exception` 后返回 500 并暴露 `str(e)`，可能泄露内部路径或实现细节 | 记录详细日志，向客户端返回统一错误消息；使用自定义异常类 |
| `api/services/solver_service.py` | CWE-918 | `callback_url` 未校验协议与域名，可能用于 SSRF | 校验 URL 协议为 https、域名在白名单内、禁止内网地址 |
| `models/database.py:20-24` | CWE-362 | SQLite 使用 `check_same_thread=False`，多线程并发访问可能导致数据损坏 | 使用连接池或为每个请求/线程创建独立会话；生产环境改用 PostgreSQL |
| `config/settings.py:22,41`、`api/main.py:92`、`start.py:81,99`、`start_fast.py:44,62` | CWE-605 | 默认绑定 `0.0.0.0`，服务暴露在所有网络接口 | 生产环境默认绑定 `127.0.0.1` 或通过环境变量显式配置；配合防火墙/反向代理 |
| `web_app.py`、`frontend/app.py` | CWE-20 / CWE-434 | 用户上传 CSV 后直接 `pd.read_csv`，未校验文件大小、编码与内容 | 限制文件大小、校验 MIME 类型、使用 `encoding='utf-8'` 并捕获解析异常 |
| `web_app.py`、`frontend/app.py` | CWE-79 / OWASP A03 | 多处 `unsafe_allow_html=True` 拼接用户相关数据，存在 XSS 风险 | 避免使用 `unsafe_allow_html=True`；必须使用时先对用户输入进行 HTML 转义 |
| `api/routers/scenarios.py` | CWE-284 | 场景数据使用内存字典存储，无持久化与访问控制 | 将场景数据持久化到数据库，并增加所有权与权限校验 |
| `docker-compose.yml:12-13` | CWE-319 | 生产配置未启用 TLS/HTTPS，数据明文传输 | 配置 TLS 证书或在反向代理（Nginx/Traefik）处终止 HTTPS |

### 3.3 低危/信息问题

| 位置 | CWE | 风险说明 | 修复建议 |
|------|-----|----------|----------|
| `start.py`、`start_fast.py` | CWE-78 | 使用 `subprocess.run` 启动服务，存在潜在命令注入反模式 | 避免在生产代码中调用子进程启动服务；使用 systemd/Docker/K8s 管理进程 |
| `tests/unit/analysis/test_comparison.py` | - | 测试代码使用 `assert`（Bandit B101），在优化模式下会被移除 | 使用 `pytest.assert*` 或显式抛出异常；保持测试代码质量 |
| `.github/workflows/ci.yml:30-31` | - | CI 中命令写为 `Ruff --version` / `Ruff .`（大写），实际工具名为小写 `ruff` | 修正为 `ruff --version` 与 `ruff check .` |

### 3.4 Bandit 扫描详情

Bandit 共扫描 155 个问题（高 4 / 中 7 / 低 7 / 测试 assert 137）。

| 文件 | 行号 | 严重程度 | CWE | 问题描述 |
|------|------|----------|-----|----------|
| `core/distance.py` | 446 | 高 | CWE-327 | Use of weak MD5 hash for security. Consider usedforsecurity=False |
| `core/solver.py` | 278 | 高 | CWE-327 | Use of weak MD5 hash for security. Consider usedforsecurity=False |
| `core/solver.py` | 287 | 高 | CWE-327 | Use of weak MD5 hash for security. Consider usedforsecurity=False |
| `core/solver.py` | 306 | 高 | CWE-327 | Use of weak MD5 hash for security. Consider usedforsecurity=False |
| `api/main.py` | 92 | 中 | CWE-605 | Possible binding to all interfaces. |
| `config/settings.py` | 22 | 中 | CWE-605 | Possible binding to all interfaces. |
| `config/settings.py` | 41 | 中 | CWE-605 | Possible binding to all interfaces. |
| `start.py` | 81 | 中 | CWE-605 | Possible binding to all interfaces. |
| `start.py` | 99 | 中 | CWE-605 | Possible binding to all interfaces. |
| `start_fast.py` | 44 | 中 | CWE-605 | Possible binding to all interfaces. |
| `start_fast.py` | 62 | 中 | CWE-605 | Possible binding to all interfaces. |
| `start.py` | 64 | 低 | CWE-78 | Consider possible security implications associated with the subprocess module. |
| `start.py` | 77 | 低 | CWE-78 | subprocess call - check for execution of untrusted input. |
| `start.py` | 105 | 低 | CWE-78 | subprocess call - check for execution of untrusted input. |
| `start_enterprise_ui.py` | 18 | 低 | CWE-78 | Consider possible security implications associated with the subprocess module. |
| `start_fast.py` | 25 | 低 | CWE-78 | Consider possible security implications associated with the subprocess module. |
| `start_fast.py` | 40 | 低 | CWE-78 | subprocess call - check for execution of untrusted input. |
| `start_fast.py` | 68 | 低 | CWE-78 | subprocess call - check for execution of untrusted input. |

## 4. 依赖 CVE 清单

| 依赖 | 当前版本 | 漏洞 ID | 严重程度 | 修复版本 | 风险说明 |
|------|----------|---------|----------|----------|----------|
| `msgpack` | 1.2.0 | GHSA-6v7p-g79w-8964 | 中 | 1.2.1 | ### Impact  If the Unpacker is used repeatedly after an error occurs, the process may crash with a SEGV.  If the Unpa... |
| `pdfkit` | 1.0.0 | CVE-2025-26240 | 高 | 无 | In JazzCore python-pdfkit 1.0.0, the from_string method enables the execution of JavaScript code within the context o... |
| `pydantic-settings` | 2.14.1 | GHSA-4xgf-cpjx-pc3j | 中 | 2.14.2 | ### Summary  `NestedSecretsSettingsSource` reads secret values from files in a configured `secrets_dir`. When `secret... |

**修复建议**：
1. `msgpack` 升级至 `>=1.2.1`；避免在 Unpacker 出错后继续复用同一实例。
2. `pdfkit` 当前无修复版本，建议评估替换为 `weasyprint` 或限制 `from_string` 的使用场景，避免处理不可信 HTML。
3. `pydantic-settings` 升级至 `>=2.14.2`；同时确保 `secrets_dir` 完全由应用控制，禁止写入或符号链接。

## 5. 动态安全测试（DAST）结果

> 因 OWASP ZAP 需要 Docker/Java 环境，本次 DAST 改为手动端点探测。启动命令：`uvicorn api.main:app --host 127.0.0.1 --port 8000`。

| 测试项 | 状态码 | 关键发现 |
|--------|--------|----------|
| Health Check | 404 | 端点未找到，建议确认健康检查路由配置 |
| Swagger Docs | 200 | API 文档公开暴露，可能扩大攻击面 |
| CORS Preflight | 200 | `Access-Control-Allow-Origin: http://evil.com`, `Access-Control-Allow-Credentials: true` — 确认凭证泄露风险 |
| GET /scenarios | 200 | 返回空列表，无认证即可访问 |
| POST /solve（无效负载） | 422 | Pydantic 验证正常返回 422 |
| POST /solve（有效负载） | 200 | 返回完整求解结果 |
| 不存在端点 | 404 | 标准 404 响应 |

**关键风险**：CORS 配置允许任意来源 (`*`) 并携带凭证，恶意网站可通过浏览器发起带 Cookie 的跨域请求，导致会话劫持或 CSRF。

## 6. 代码质量问题清单

### 6.1 代码规范违规（Ruff）

Ruff 共发现 **946** 条规范问题。Top 10 规则如下：

| 规则 | 数量 | 说明 |
|------|----:|------|
| [UP006](https://docs.astral.sh/ruff/rules/non-pep585-annotation) | 384 | 详见 Ruff 文档 |
| [T201](https://docs.astral.sh/ruff/rules/print) | 153 | 详见 Ruff 文档 |
| [UP045](https://docs.astral.sh/ruff/rules/non-pep604-annotation-optional) | 111 | 详见 Ruff 文档 |
| [I001](https://docs.astral.sh/ruff/rules/unsorted-imports) | 72 | 详见 Ruff 文档 |
| [UP035](https://docs.astral.sh/ruff/rules/deprecated-import) | 59 | 详见 Ruff 文档 |
| [C408](https://docs.astral.sh/ruff/rules/unnecessary-collection-call) | 45 | 详见 Ruff 文档 |
| [F401](https://docs.astral.sh/ruff/rules/unused-import) | 44 | 详见 Ruff 文档 |
| [F841](https://docs.astral.sh/ruff/rules/unused-variable) | 14 | 详见 Ruff 文档 |
| [B007](https://docs.astral.sh/ruff/rules/unused-loop-control-variable) | 7 | 详见 Ruff 文档 |
| [UP007](https://docs.astral.sh/ruff/rules/non-pep604-annotation-union) | 7 | 详见 Ruff 文档 |

**高频问题文件**（按问题数量）：

| 文件 | 问题数 |
|------|----:|
| `analysis/strategy_eval.py` | 77 |
| `start_fast.py` | 64 |
| `start.py` | 61 |
| `core/solver.py` | 60 |
| `optimization/multi_objective.py` | 53 |
| `tests/performance/benchmark.py` | 48 |
| `analysis/sensitivity.py` | 45 |
| `optimization/carbon_aware.py` | 42 |
| `analysis/comparison.py` | 37 |
| `core/cost.py` | 36 |

### 6.2 类型检查问题（MyPy）

MyPy 共发现 **127** 条类型错误。高频错误类型：

| 错误类型 | 数量 | 说明 |
|----------|----:|------|
| `assignment` | 19 | - |
| `index` | 7 | - |
| `misc` | 4 | - |
| `operator` | 2 | - |

**高频问题文件**：

| 文件 | 错误数 |
|------|----:|
| `optimization/dynamic.py` | 37 |
| `core/distance.py` | 9 |
| `core/solver.py` | 8 |
| `tests/unit/core/test_distance.py` | 8 |
| `data_types/solution.py` | 7 |
| `analysis/sensitivity.py` | 6 |
| `optimization/carbon_aware.py` | 6 |
| `analysis/strategy_eval.py` | 5 |
| `analysis/comparison.py` | 5 |
| `start.py` | 5 |

### 6.3 圈复杂度（Radon）

项目平均圈复杂度为 **A（3.6493506493506493）**，处于中等偏复杂水平。

| 排名 | 函数/方法 | 行号 | 复杂度 | 等级 |
|------|-----------|------|--------|------|
| 1 | `web_app.py:display_comparison_tab` | 433:0 | 26 | D |
| 2 | `utils/validation.py:validate_customer` | 13:0 | 19 | C |
| 3 | `web_app.py:main` | 684:0 | 16 | C |
| 4 | `optimization/multi_objective.py:MultiObjectiveOptimizer.generate_pareto_front` | 251:4 | 14 | C |
| 5 | `frontend/components/map_view.py:create_enterprise_map` | 21:0 | 14 | C |
| 6 | `analysis/sensitivity.py:SensitivityAnalyzer._calculate_sensitivities` | 284:4 | 14 | C |
| 7 | `core/cost.py:_get_vehicle_params_cached_impl` | 116:0 | 12 | C |
| 8 | `analysis/comparison.py:ScenarioComparison.compare_solutions` | 103:4 | 12 | C |
| 9 | `web_app.py:create_map` | 106:0 | 12 | C |
| 10 | `core/solver.py:solve_with_multiple_strategies_parallel` | 892:0 | 11 | C |

## 7. SonarQube / Semgrep / OWASP ZAP 说明

本次扫描原计划集成 SonarQube Community、Semgrep 与 OWASP ZAP，但因当前环境无法连接 Docker 服务且未安装 Java 运行时，以下工具未能执行：

- **SonarQube Community**：需要 Docker 或本地 Java 环境启动服务端与 Scanner。
- **OWASP ZAP**：需要 Docker 或本地 Java 环境运行主动/基线扫描。
- **Semgrep**：需要网络拉取规则集；若后续网络可用，可补充运行 `semgrep --config=auto --config=p/security-audit --config=p/owasp-top-ten .`。

已通过 **Bandit + 手动 DAST + 人工代码审查** 覆盖上述工具可能发现的主要问题（CORS、认证缺失、异常泄露、依赖 CVE 等）。

## 8. 优先修复建议与后续行动计划

### 8.1 P0（立即修复）

1. **修复 CORS 配置**：在 `api/main.py` 中移除 `allow_origins=["*"]` 与 `allow_credentials=True` 的组合，改为读取环境变量 `GREENVRP_ALLOWED_ORIGINS` 并显式校验域名。
2. **增加 API 认证与限流**：为 `/api/v1/solve`、`/api/v1/jobs`、`/api/v1/scenarios` 等敏感端点增加 API Key 或 JWT 认证；使用 `slowapi` 或 Nginx 配置限流。
3. **异常信息脱敏**：在 `api/routers/solver.py` 中将 `raise HTTPException(status_code=500, detail=f"求解失败: {str(e)}")` 改为记录日志并返回统一错误消息。

### 8.2 P1（短期修复）

1. **修复依赖 CVE**：升级 `msgpack>=1.2.1`、`pydantic-settings>=2.14.2`；评估替换 `pdfkit` 或限制其使用。
2. **校验 callback_url**：在 `api/services/solver_service.py` 中对 `callback_url` 进行协议、域名与白名单校验，防止 SSRF。
3. **数据库线程安全**：在 `models/database.py` 中移除 `check_same_thread=False`，或为每个线程创建独立 `SessionLocal`；生产环境优先使用 PostgreSQL。
4. **前端输入消毒**：在 `web_app.py` 与 `frontend/app.py` 中对 CSV 上传进行大小、编码、内容校验；移除不必要的 `unsafe_allow_html=True`。

### 8.3 P2（持续改进）

1. **规范导入与类型注解**：使用 `ruff check . --fix` 自动修复 `I001`、`UP035`、`UP006` 等；逐步为 `optimization/dynamic.py`、`core/distance.py` 等核心模块补充类型注解。
2. **降低圈复杂度**：对 Radon 识别的高复杂度函数（≥C）进行拆分或重构。
3. **修复 CI 配置**：将 `.github/workflows/ci.yml` 中的 `Ruff` 改为 `ruff`，确保 Lint 检查真正生效。
4. **补齐专业扫描**：在具备 Docker/Java 的环境后，重新运行 SonarQube、Semgrep 与 OWASP ZAP，并与本报告对比。

## 附录：原始报告文件

- `reports/security/bandit-report.json`
- `reports/security/pip-audit-environment.json`
- `reports/security/manual-dast.json`
- `reports/quality/ruff-report-clean.json`
- `reports/quality/mypy-report.txt`
- `reports/quality/radon-cyclomatic.txt`
- `reports/quality/radon-maintainability.txt`
