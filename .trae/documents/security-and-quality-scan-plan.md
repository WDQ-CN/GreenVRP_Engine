# GreenVRP Engine 安全漏洞扫描与代码质量评估执行计划（修订版）

## 1. 摘要

对 `d:\ZhuoMian\GreenVRP_Engine` 项目执行全面的安全漏洞扫描与代码质量评估。原计划使用 Docker 运行 SonarQube 与 OWASP ZAP，但因当前环境无法连接 Docker 服务，已调整为 **Python 原生工具链 + 手动 DAST 测试** 完成扫描。本计划用于指导最后一步：汇总所有工具输出并生成结构化 Markdown 最终报告。

- **已完成扫描**：Bandit（SAST）、pip-audit（依赖 CVE）、Ruff（代码规范）、MyPy（类型检查）、Radon（复杂度/可维护性）、手动端点 DAST。
- **无法执行**：SonarQube（需 Docker/Java）、OWASP ZAP（需 Docker/Java）、Semgrep（网络拉取规则受限，可选）。
- **最终交付物**：`reports/GreenVRP_Security_Quality_Scan_Report.md`。

---

## 2. 项目现状分析

### 2.1 技术栈与架构

- **语言**：Python（环境中为 3.14，项目声明支持 3.10–3.12）
- **后端框架**：FastAPI，`api/main.py` 为入口
- **前端**：Streamlit（`web_app.py`、`frontend/app.py`）
- **数据库**：SQLAlchemy 2.0+，默认 SQLite（`models/database.py`）
- **优化求解**：OR-Tools（`core/solver.py`、`core/distance.py`）
- **数据验证**：Pydantic v2（`api/schemas/request.py`）
- **质量工具**：Ruff、MyPy、pytest、coverage（已配置在 `pyproject.toml`）

### 2.2 已确认的关键风险点

| 位置 | 问题 | 严重程度 | 风险说明 |
|------|------|----------|----------|
| `api/main.py:63-74` | CORS 默认 `allow_origins=["*"]` 且 `allow_credentials=True` | 高 | 任意来源可携带凭证访问 API，存在会话劫持/CSRF 风险 |
| `api/main.py`、`api/routers/*.py` | 无认证、授权、Rate Limit、API Key | 高 | API 完全开放，可被未授权调用或 DoS |
| `api/routers/solver.py:58-59`、`api/routers/solver.py:98-99` | 捕获 `Exception` 后返回 500 并暴露 `str(e)` | 中 | 内部错误信息泄露，可能暴露路径或实现细节 |
| `models/database.py:20-24` | SQLite `check_same_thread=False` | 中 | 线程安全问题，可能导致数据损坏 |
| `api/services/solver_service.py` | `callback_url` 未校验协议与地址，直接用于回调 | 中 | 潜在的 SSRF（服务端请求伪造） |
| `core/distance.py:446`、`core/solver.py:278,287,306` | 使用 `hashlib.md5` 且未标记 `usedforsecurity=False` | 高/中 | 弱哈希算法，存在碰撞风险（虽用于缓存键，仍应显式声明） |
| `config/settings.py:22,41`、`api/main.py:92`、`start.py:81,99`、`start_fast.py:44,62` | 默认绑定 `0.0.0.0` | 中 | 服务暴露在所有网络接口，扩大攻击面 |
| `web_app.py`、`frontend/app.py` | 用户上传 CSV 后直接 `pd.read_csv`，无文件大小/编码/内容消毒 | 中 | CSV 注入/解析拒绝服务/路径遍历风险 |
| `web_app.py`、`frontend/app.py` | 多处使用 `unsafe_allow_html=True` 拼接用户相关数据 | 中 | 潜在的反射型/存储型 XSS |
| `api/routers/scenarios.py` | 场景数据使用内存字典存储 | 中 | 数据无持久化、无访问控制、服务重启丢失 |
| `start.py`、`start_fast.py` | 使用 `subprocess.run` 启动服务 | 低 | 命令注入风险较低，但属于需要关注的安全反模式 |

### 2.3 依赖 CVE（已确认）

| 依赖 | 版本 | 漏洞 ID | 严重程度 | 修复版本 | 说明 |
|------|------|---------|----------|----------|------|
| `msgpack` | 1.2.0 | GHSA-6v7p-g79w-8964 | 中 | 1.2.1 | Unpacker 错误复用可导致 SEGV/DoS |
| `pdfkit` | 1.0.0 | CVE-2025-26240 | 高 | 无 | `from_string` 方法可执行 JS 并窃取本地文件 |
| `pydantic-settings` | 2.14.1 | GHSA-4xgf-cpjx-pc3j | 中 | 2.14.2 | `NestedSecretsSettingsSource` 跟随符号链接读取 secrets_dir 外文件 |

### 2.4 代码质量概况

- **Ruff**：大量 `I001`（导入未排序）、`UP035`（已弃用 typing 导入）等规范问题；存在部分 `E501` 行过长、`F401` 未使用导入。
- **MyPy**：多处类型不兼容、返回 `Any`、`None` 未处理、缺少类型注解，集中在 `optimization/dynamic.py`、`core/distance.py`、`analysis/*.py`。
- **Radon**：平均圈复杂度 **C（13.8）**，存在多个高复杂度函数，维护性指数总体尚可（`utils/__init__.py` 为 A）。

### 2.5 动态测试（手动 DAST）

- 启动 `uvicorn api.main:app --host 127.0.0.1 --port 8000` 后进行端点探测。
- 关键发现：
  - `/api/v1/health` 实际不存在（404），与健康检查预期不符。
  - CORS 预检响应返回 `Access-Control-Allow-Origin: http://evil.com` 且 `Access-Control-Allow-Credentials: true`，确认存在 CORS 凭证泄露风险。
  - `/docs` 暴露 Swagger UI，可能扩大攻击面。
  - 求解接口对无效负载返回 422 验证错误（正常），对有效负载返回完整路径与成本信息。

---

## 3. 计划步骤

### Phase A：数据整理（已完成 → 复核）

1. 确认以下报告文件存在且内容完整：
   - `reports/security/bandit-report.json`
   - `reports/security/pip-audit-environment.json`
   - `reports/security/manual-dast.json`
   - `reports/quality/ruff-report.json`
   - `reports/quality/mypy-report.txt`
   - `reports/quality/radon-cyclomatic.txt`
   - `reports/quality/radon-maintainability.txt`
   - `reports/quality/radon-raw.txt`
2. 对 Bandit 报告进行聚合统计（按严重等级、按文件）。
3. 对 Ruff 报告进行聚合统计（按规则、按文件）。
4. 对 MyPy 报告进行聚合统计（按错误类型、按文件）。
5. 对 Radon 报告提取最高复杂度函数 TOP10。

### Phase B：补充人工代码审查（可选但建议）

针对工具未能覆盖的以下点进行静态审查并写入报告：

- `web_app.py` 与 `frontend/app.py` 的 `unsafe_allow_html=True` 使用点。
- `api/services/solver_service.py` 中 `callback_url` 的调用逻辑。
- `core/solver.py` 与 `core/distance.py` 中 `md5` 的实际用途与上下文。
- `models/database.py` 的 `check_same_thread=False` 使用上下文。
- `docker-compose.yml` 中是否暴露敏感环境变量或缺少 TLS。
- `.github/workflows/ci.yml` 中 `Ruff` 大写命令导致 CI 失效的问题。

### Phase C：生成最终 Markdown 报告

在 `reports/GreenVRP_Security_Quality_Scan_Report.md` 中按以下结构输出：

1. **执行摘要**
   - 总体风险等级（高）
   - 扫描工具与方法概述
   - 问题数量统计表（安全高/中/低/信息，质量错误/警告，CVE 数量）
2. **扫描范围与方法**
   - 扫描范围：`api/`、`core/`、`models/`、`config/`、`frontend/`、`web_app.py`、`start*.py` 等
   - 工具链说明与 Docker 不可用导致的工具降级说明
   - 排除项：`.venv/`、`.git/`、`__pycache__/`、测试中的 `assert` 等
3. **安全漏洞清单**
   - 按严重程度高/中/低/信息排序
   - 每行包含：位置（文件:行号）、CWE/OWASP 分类、严重程度、风险说明、修复建议
4. **依赖 CVE 清单**
   - 列出 `msgpack`、`pdfkit`、`pydantic-settings` 的 CVE 详情与修复建议
5. **代码质量问题清单**
   - 规范违规（Ruff）：I001、UP035、F401、E501 等 TOP 规则
   - 类型问题（MyPy）：按文件统计的高频问题
   - 复杂度过高/重复代码（Radon）：平均复杂度 C（13.8），列出 TOP10 复杂函数
   - 不可达代码、裸 except、print 语句等人工审查发现
6. **DAST 结果**
   - 手动端点探测结果（health、docs、cors_preflight、scenarios、solve、not_found）
   - CORS 凭证泄露风险说明
7. **SonarQube / Semgrep / ZAP 关键问题摘要**
   - 说明因环境限制未能运行，并列出基于人工审查的等效发现
8. **优先修复建议与后续行动计划**
   - P0：修复 CORS 配置、增加认证/限流
   - P1：修复依赖 CVE、异常信息脱敏、callback_url 校验
   - P2：规范导入与类型注解、降低圈复杂度、修复 CI 命令大小写

---

## 4. 假设与决策

1. **Docker 不可用**：当前环境无法连接 Docker 服务，已确认无法运行 SonarQube 与 OWASP ZAP；最终报告将明确标注该限制。
2. **不修改代码**：本阶段仅生成报告，不直接修复发现的问题；修复建议将在报告中给出。
3. **依赖扫描范围**：仅扫描当前 Python 环境已安装依赖（`pip-audit --format=json`），不扫描 `requirements.txt` 中未安装或冲突版本。
4. **测试代码中的 `assert`**：Bandit 在 `tests/unit/analysis/test_comparison.py` 中报告大量 B101，属于测试代码特性，报告中单独标注为“信息/低危”。
5. **报告语言**：报告采用中文，与用户要求一致。

---

## 5. 验证步骤

1. `reports/GreenVRP_Security_Quality_Scan_Report.md` 文件成功生成。
2. 报告包含至少 5 个高/中危安全问题和 5 个代码质量问题。
3. 报告中明确列出 3 个已知依赖 CVE 及其修复版本。
4. 报告中说明 Docker/SonarQube/ZAP 因环境限制未执行的原因。
5. 最终向用户展示报告路径，并简要总结 3–5 条最关键的发现。
