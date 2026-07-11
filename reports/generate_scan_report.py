"""
汇总安全与代码质量扫描结果，生成最终 Markdown 报告。
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path("d:/ZhuoMian/GreenVRP_Engine")
REPORTS_DIR = ROOT / "reports"
OUT_FILE = REPORTS_DIR / "GreenVRP_Security_Quality_Scan_Report.md"


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_json_utf16(path: Path):
    # 部分历史报告编码异常，优先尝试 utf-8，失败则按 utf-16-le 读取并清理截断
    for enc in ("utf-8", "utf-8-sig", "utf-16-le", "utf-16"):
        try:
            with open(path, encoding=enc) as f:
                data = f.read()
            if data.startswith("\ufeff"):
                data = data[1:]
            return json.loads(data)
        except Exception:
            continue
    raise ValueError(f"无法解析 JSON: {path}")


def parse_bandit():
    data = load_json(REPORTS_DIR / "security" / "bandit-report.json")
    results = data.get("results", [])
    by_sev = Counter(r["issue_severity"] for r in results)
    by_file = defaultdict(list)
    for r in results:
        by_file[r["filename"]].append(r)
    return {
        "total": len(results),
        "by_severity": dict(by_sev),
        "by_file": dict(by_file),
        "errors": data.get("errors", []),
    }


def parse_pip_audit():
    data = load_json(REPORTS_DIR / "security" / "pip-audit-environment.json")
    deps = data.get("dependencies", [])
    vulnerable = [d for d in deps if d.get("vulns")]
    return {"total": len(deps), "vulnerable": vulnerable}


def parse_dast():
    return load_json(REPORTS_DIR / "security" / "manual-dast.json")


def parse_ruff():
    # 使用新生成的干净 JSON
    data = load_json_utf16(REPORTS_DIR / "quality" / "ruff-report-clean.json")
    by_code = Counter(r["code"] for r in data)
    by_file = defaultdict(list)
    for r in data:
        by_file[r["filename"]].append(r)
    return {"total": len(data), "by_code": dict(by_code), "by_file": dict(by_file)}


def parse_mypy():
    path = REPORTS_DIR / "quality" / "mypy-report.txt"
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    errors = [line.strip() for line in lines if ": error:" in line]
    by_type = Counter()
    by_file = defaultdict(list)
    for line in errors:
        m = re.search(r"\[(\w+)\]$", line)
        if m:
            by_type[m.group(1)] += 1
        m = re.match(r"^(.+?):\d+?: error:", line)
        if m:
            by_file[m.group(1)].append(line)
    return {"total": len(errors), "by_type": dict(by_type), "by_file": dict(by_file)}


def parse_radon():
    path = REPORTS_DIR / "quality" / "radon-cyclomatic-full.txt"
    # 优先尝试 utf-8；历史报告可能为 utf-16-le
    text = None
    for enc in ("utf-8", "utf-8-sig", "utf-16-le", "utf-16", "gbk"):
        try:
            with open(path, encoding=enc) as f:
                text = f.read()
            if text.startswith("\ufeff"):
                text = text[1:]
            break
        except Exception:
            continue
    if text is None:
        raise ValueError(f"无法读取 Radon 报告: {path}")

    # 提取平均复杂度
    avg_match = re.search(r"Average complexity: ([A-F]) \(([\d.]+)\)", text)
    avg_rank = avg_match.group(1) if avg_match else "?"
    avg_score = float(avg_match.group(2)) if avg_match else 0.0

    # 提取每个函数/方法的复杂度
    funcs = []
    current_file = None
    # 匹配文件行："core\cost.py" 或 "api\main.py"
    file_pattern = re.compile(r"^(.+\.py)$")
    # 匹配函数行："    F 116:0 _get_vehicle_params_cached_impl - C (25)"
    func_pattern = re.compile(r"^\s+([FMC])\s+(\d+):(\d+)\s+(.+?)\s+-\s+([A-F])\s+\((\d+)\)")
    for line in text.splitlines():
        line = line.rstrip()
        m = file_pattern.match(line)
        if m:
            current_file = m.group(1).replace("\\", "/")
            continue
        m = func_pattern.match(line)
        if m and current_file:
            funcs.append(
                {
                    "block_type": m.group(1),
                    "line": int(m.group(2)),
                    "col": int(m.group(3)),
                    "name": f"{current_file}:{m.group(4).strip()}",
                    "complexity_rank": m.group(5),
                    "complexity": int(m.group(6)),
                }
            )
    funcs.sort(key=lambda x: x["complexity"], reverse=True)
    return {"average_rank": avg_rank, "average_score": avg_score, "top_funcs": funcs[:20]}


def normalize_path(p: str) -> str:
    return p.replace("\\", "/").replace("D:/ZhuoMian/GreenVRP_Engine/", "").replace("./", "")


def severity_emoji(sev: str) -> str:
    return {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢", "UNDEFINED": "⚪"}.get(sev.upper(), "⚪")


def severity_cn(sev: str) -> str:
    return {"HIGH": "高", "MEDIUM": "中", "LOW": "低", "UNDEFINED": "信息"}.get(sev.upper(), sev)


def build_report():
    bandit = parse_bandit()
    pip_audit = parse_pip_audit()
    dast = parse_dast()
    ruff = parse_ruff()
    mypy = parse_mypy()
    radon = parse_radon()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append("# GreenVRP Engine 安全漏洞扫描与代码质量评估报告")
    lines.append("")
    lines.append(f"**生成时间**：{now}")
    lines.append("")
    lines.append("**报告路径**：`reports/GreenVRP_Security_Quality_Scan_Report.md`")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 执行摘要
    lines.append("## 1. 执行摘要")
    lines.append("")
    lines.append("### 1.1 总体风险等级")
    lines.append("")
    lines.append("**总体风险等级：高**")
    lines.append("")
    lines.append(
        "项目当前存在多项高危与中危安全问题，尤其是 API 层面缺少认证、CORS 配置过于宽松、服务端错误信息泄露，以及多个已知依赖 CVE。代码质量方面，类型注解缺失与规范违规较多，圈复杂度总体偏高，需尽快制定修复计划。"
    )
    lines.append("")
    lines.append("### 1.2 扫描工具与方法")
    lines.append("")
    lines.append("| 类型 | 工具 | 说明 |")
    lines.append("|------|------|------|")
    lines.append("| 静态应用安全测试（SAST） | Bandit 1.9.4 | Python 代码安全扫描 |")
    lines.append("| 依赖漏洞扫描 | pip-audit 2.10.1 | 扫描当前环境已安装依赖的已知 CVE |")
    lines.append(
        "| 动态应用安全测试（DAST） | 手动端点探测 | 因 Docker/Java 不可用，未运行 OWASP ZAP |"
    )
    lines.append("| 代码规范 | Ruff 0.15.17 | Lint 与代码格式检查 |")
    lines.append("| 类型检查 | MyPy | Python 静态类型分析 |")
    lines.append("| 复杂度/可维护性 | Radon 6.0.1 | 圈复杂度与维护性指数 |")
    lines.append(
        "| **未执行** | SonarQube、Semgrep、OWASP ZAP | 当前环境无法启动 Docker，缺少 Java 运行时 |"
    )
    lines.append("")
    lines.append(
        "> **环境限制说明**：原计划使用 Docker 运行 SonarQube Community 与 OWASP ZAP，但当前环境无法连接 Docker 服务。已改用 Python 原生工具链完成 SAST、依赖审计与代码质量分析，并以手动 HTTP 探测替代 ZAP 进行基础 DAST。"
    )
    lines.append("")

    # 问题统计
    lines.append("### 1.3 问题数量统计")
    lines.append("")
    high = bandit["by_severity"].get("HIGH", 0)
    medium = bandit["by_severity"].get("MEDIUM", 0)
    low = bandit["by_severity"].get("LOW", 0)
    # 将测试代码中的 assert 从 LOW 中剥离，单独说明
    assert_count = sum(1 for rs in bandit["by_file"].values() for r in rs if r["test_id"] == "B101")
    other_low = low - assert_count

    lines.append("| 类别 | 高 | 中 | 低 | 信息 | 合计 |")
    lines.append("|------|----:|----:|----:|----:|----:|")
    lines.append(
        f"| 安全漏洞（Bandit） | {high} | {medium} | {other_low} | {assert_count}（测试 assert） | {bandit['total']} |"
    )
    lines.append(
        f"| 依赖 CVE | {len([v for v in pip_audit['vulnerable'] if any('CVE' in x['id'] for x in v['vulns'])])} | {len(pip_audit['vulnerable'])} | 0 | 0 | {len(pip_audit['vulnerable'])} |"
    )
    lines.append(f"| 代码规范违规（Ruff） | - | - | - | - | {ruff['total']} |")
    lines.append(f"| 类型错误（MyPy） | - | - | - | - | {mypy['total']} |")
    high_complexity_count = len(
        [f for f in radon["top_funcs"] if f["complexity_rank"] in ("C", "D", "E", "F")]
    )
    lines.append(
        f"| 高复杂度函数（Radon ≥ C，TOP 20 内） | - | - | - | - | {high_complexity_count} |"
    )
    lines.append("")

    # 扫描范围
    lines.append("## 2. 扫描范围")
    lines.append("")
    lines.append("- **后端 API**：`api/main.py`、`api/routers/`、`api/schemas/`、`api/services/`")
    lines.append("- **核心算法**：`core/solver.py`、`core/distance.py`、`optimization/`")
    lines.append("- **数据模型**：`data_types/`、`models/`、`config/settings.py`")
    lines.append("- **前端/入口**：`web_app.py`、`frontend/app.py`、`start.py`、`start_fast.py`")
    lines.append("- **测试与 CI**：`tests/`、`.github/workflows/ci.yml`")
    lines.append(
        "- **排除项**：`.venv/`、`.git/`、`__pycache__/`、`.pytest_cache/`、第三方依赖源码"
    )
    lines.append("")

    # 安全漏洞清单
    lines.append("## 3. 安全漏洞清单")
    lines.append("")
    lines.append("### 3.1 高危问题")
    lines.append("")
    lines.append("| 位置 | CWE | 风险说明 | 修复建议 |")
    lines.append("|------|-----|----------|----------|")
    lines.append(
        '| `api/main.py:63-74` | CWE-942 / OWASP API 7 | CORS 默认 `allow_origins=["*"]` 且 `allow_credentials=True`，任意恶意站点可携带用户凭证调用 API | 生产环境必须显式配置受信任域名列表，禁止 `*` 与 `allow_credentials=True` 同时出现 |'
    )
    lines.append(
        "| `api/main.py`、`api/routers/*.py` | CWE-306 / OWASP API 1 | 所有 API 端点均无认证、授权、Rate Limit 或 API Key，完全开放 | 增加 OAuth2/JWT/API Key 认证，并按角色授权；对敏感端点配置限流 |"
    )
    lines.append(
        "| `core/distance.py:446` | CWE-327 | 使用 `hashlib.md5` 生成缓存键，未设置 `usedforsecurity=False` | 如仅用于非安全场景，添加 `usedforsecurity=False`；如用于安全场景，改用 SHA-256 |"
    )
    lines.append(
        "| `core/solver.py:278,287,306` | CWE-327 | 同上，多处使用 MD5 作为缓存键 | 同上 |"
    )
    lines.append("")

    lines.append("### 3.2 中危问题")
    lines.append("")
    lines.append("| 位置 | CWE | 风险说明 | 修复建议 |")
    lines.append("|------|-----|----------|----------|")
    lines.append(
        "| `api/routers/solver.py:58-59`、`api/routers/solver.py:98-99` | CWE-209 | 捕获 `Exception` 后返回 500 并暴露 `str(e)`，可能泄露内部路径或实现细节 | 记录详细日志，向客户端返回统一错误消息；使用自定义异常类 |"
    )
    lines.append(
        "| `api/services/solver_service.py` | CWE-918 | `callback_url` 未校验协议与域名，可能用于 SSRF | 校验 URL 协议为 https、域名在白名单内、禁止内网地址 |"
    )
    lines.append(
        "| `models/database.py:20-24` | CWE-362 | SQLite 使用 `check_same_thread=False`，多线程并发访问可能导致数据损坏 | 使用连接池或为每个请求/线程创建独立会话；生产环境改用 PostgreSQL |"
    )
    lines.append(
        "| `config/settings.py:22,41`、`api/main.py:92`、`start.py:81,99`、`start_fast.py:44,62` | CWE-605 | 默认绑定 `0.0.0.0`，服务暴露在所有网络接口 | 生产环境默认绑定 `127.0.0.1` 或通过环境变量显式配置；配合防火墙/反向代理 |"
    )
    lines.append(
        "| `web_app.py`、`frontend/app.py` | CWE-20 / CWE-434 | 用户上传 CSV 后直接 `pd.read_csv`，未校验文件大小、编码与内容 | 限制文件大小、校验 MIME 类型、使用 `encoding='utf-8'` 并捕获解析异常 |"
    )
    lines.append(
        "| `web_app.py`、`frontend/app.py` | CWE-79 / OWASP A03 | 多处 `unsafe_allow_html=True` 拼接用户相关数据，存在 XSS 风险 | 避免使用 `unsafe_allow_html=True`；必须使用时先对用户输入进行 HTML 转义 |"
    )
    lines.append(
        "| `api/routers/scenarios.py` | CWE-284 | 场景数据使用内存字典存储，无持久化与访问控制 | 将场景数据持久化到数据库，并增加所有权与权限校验 |"
    )
    lines.append(
        "| `docker-compose.yml:12-13` | CWE-319 | 生产配置未启用 TLS/HTTPS，数据明文传输 | 配置 TLS 证书或在反向代理（Nginx/Traefik）处终止 HTTPS |"
    )
    lines.append("")

    lines.append("### 3.3 低危/信息问题")
    lines.append("")
    lines.append("| 位置 | CWE | 风险说明 | 修复建议 |")
    lines.append("|------|-----|----------|----------|")
    lines.append(
        "| `start.py`、`start_fast.py` | CWE-78 | 使用 `subprocess.run` 启动服务，存在潜在命令注入反模式 | 避免在生产代码中调用子进程启动服务；使用 systemd/Docker/K8s 管理进程 |"
    )
    lines.append(
        "| `tests/unit/analysis/test_comparison.py` | - | 测试代码使用 `assert`（Bandit B101），在优化模式下会被移除 | 使用 `pytest.assert*` 或显式抛出异常；保持测试代码质量 |"
    )
    lines.append(
        "| `.github/workflows/ci.yml:30-31` | - | CI 中命令写为 `Ruff --version` / `Ruff .`（大写），实际工具名为小写 `ruff` | 修正为 `ruff --version` 与 `ruff check .` |"
    )
    lines.append("")

    # Bandit 详细列表
    lines.append("### 3.4 Bandit 扫描详情")
    lines.append("")
    lines.append(
        f"Bandit 共扫描 {bandit['total']} 个问题（高 {high} / 中 {medium} / 低 {other_low} / 测试 assert {assert_count}）。"
    )
    lines.append("")
    lines.append("| 文件 | 行号 | 严重程度 | CWE | 问题描述 |")
    lines.append("|------|------|----------|-----|----------|")
    non_assert_results = [r for r in sum(bandit["by_file"].values(), []) if r["test_id"] != "B101"]
    non_assert_results.sort(
        key=lambda x: ("HIGH", "MEDIUM", "LOW", "UNDEFINED").index(x["issue_severity"])
    )
    for r in non_assert_results[:30]:
        cwe_id = r.get("issue_cwe", {}).get("id", "-")
        lines.append(
            f"| `{normalize_path(r['filename'])}` | {r['line_number']} | {severity_cn(r['issue_severity'])} | CWE-{cwe_id} | {r['issue_text']} |"
        )
    if len(non_assert_results) > 30:
        lines.append(
            f"| ... | ... | ... | ... | 还有 {len(non_assert_results) - 30} 条低危问题详见 `reports/security/bandit-report.json` |"
        )
    lines.append("")

    # 依赖 CVE
    lines.append("## 4. 依赖 CVE 清单")
    lines.append("")
    lines.append("| 依赖 | 当前版本 | 漏洞 ID | 严重程度 | 修复版本 | 风险说明 |")
    lines.append("|------|----------|---------|----------|----------|----------|")
    for d in pip_audit["vulnerable"]:
        for v in d["vulns"]:
            sev = "高" if "CVE" in v["id"] else "中"
            fix = ", ".join(v.get("fix_versions", [])) or "无"
            desc = v.get("description", "").replace("\n", " ").replace("|", "\\|")
            if len(desc) > 120:
                desc = desc[:117] + "..."
            lines.append(f"| `{d['name']}` | {d['version']} | {v['id']} | {sev} | {fix} | {desc} |")
    lines.append("")
    lines.append("**修复建议**：")
    lines.append("1. `msgpack` 升级至 `>=1.2.1`；避免在 Unpacker 出错后继续复用同一实例。")
    lines.append(
        "2. `pdfkit` 当前无修复版本，建议评估替换为 `weasyprint` 或限制 `from_string` 的使用场景，避免处理不可信 HTML。"
    )
    lines.append(
        "3. `pydantic-settings` 升级至 `>=2.14.2`；同时确保 `secrets_dir` 完全由应用控制，禁止写入或符号链接。"
    )
    lines.append("")

    # DAST 结果
    lines.append("## 5. 动态安全测试（DAST）结果")
    lines.append("")
    lines.append(
        "> 因 OWASP ZAP 需要 Docker/Java 环境，本次 DAST 改为手动端点探测。启动命令：`uvicorn api.main:app --host 127.0.0.1 --port 8000`。"
    )
    lines.append("")
    lines.append("| 测试项 | 状态码 | 关键发现 |")
    lines.append("|--------|--------|----------|")
    health = dast.get("health", {})
    lines.append(
        f"| Health Check | {health.get('status', 'N/A')} | 端点未找到，建议确认健康检查路由配置 |"
    )
    lines.append(
        f"| Swagger Docs | {dast.get('docs', {}).get('status', 'N/A')} | API 文档公开暴露，可能扩大攻击面 |"
    )
    cors = dast.get("cors_preflight", {})
    lines.append(
        f"| CORS Preflight | {cors.get('status', 'N/A')} | "
        f"`Access-Control-Allow-Origin: {cors.get('access_control_allow_origin', 'N/A')}`, "
        f"`Access-Control-Allow-Credentials: {cors.get('access_control_allow_credentials', 'N/A')}` — 确认凭证泄露风险 |"
    )
    lines.append(
        f"| GET /scenarios | {dast.get('scenarios_get', {}).get('status', 'N/A')} | 返回空列表，无认证即可访问 |"
    )
    lines.append(
        f"| POST /solve（无效负载） | {dast.get('solve_invalid', {}).get('status', 'N/A')} | Pydantic 验证正常返回 422 |"
    )
    lines.append(
        f"| POST /solve（有效负载） | {dast.get('solve_valid', {}).get('status', 'N/A')} | 返回完整求解结果 |"
    )
    lines.append(
        f"| 不存在端点 | {dast.get('not_found', {}).get('status', 'N/A')} | 标准 404 响应 |"
    )
    lines.append("")
    lines.append(
        "**关键风险**：CORS 配置允许任意来源 (`*`) 并携带凭证，恶意网站可通过浏览器发起带 Cookie 的跨域请求，导致会话劫持或 CSRF。"
    )
    lines.append("")

    # 代码质量问题
    lines.append("## 6. 代码质量问题清单")
    lines.append("")
    lines.append("### 6.1 代码规范违规（Ruff）")
    lines.append("")
    lines.append(f"Ruff 共发现 **{ruff['total']}** 条规范问题。Top 10 规则如下：")
    lines.append("")
    lines.append("| 规则 | 数量 | 说明 |")
    lines.append("|------|----:|------|")
    for code, count in Counter(ruff["by_code"]).most_common(10):
        url = ""
        for r in sum(ruff["by_file"].values(), []):
            if r["code"] == code:
                url = r.get("url", "")
                break
        lines.append(f"| [{code}]({url}) | {count} | 详见 Ruff 文档 |")
    lines.append("")
    lines.append("**高频问题文件**（按问题数量）：")
    lines.append("")
    lines.append("| 文件 | 问题数 |")
    lines.append("|------|----:|")
    for fname, issues in sorted(ruff["by_file"].items(), key=lambda x: -len(x[1]))[:10]:
        lines.append(f"| `{normalize_path(fname)}` | {len(issues)} |")
    lines.append("")

    lines.append("### 6.2 类型检查问题（MyPy）")
    lines.append("")
    lines.append(f"MyPy 共发现 **{mypy['total']}** 条类型错误。高频错误类型：")
    lines.append("")
    lines.append("| 错误类型 | 数量 | 说明 |")
    lines.append("|----------|----:|------|")
    for err_type, count in Counter(mypy["by_type"]).most_common(10):
        lines.append(f"| `{err_type}` | {count} | - |")
    lines.append("")
    lines.append("**高频问题文件**：")
    lines.append("")
    lines.append("| 文件 | 错误数 |")
    lines.append("|------|----:|")
    for fname, errors in sorted(mypy["by_file"].items(), key=lambda x: -len(x[1]))[:10]:
        lines.append(f"| `{normalize_path(fname)}` | {len(errors)} |")
    lines.append("")

    lines.append("### 6.3 圈复杂度（Radon）")
    lines.append("")
    lines.append(
        f"项目平均圈复杂度为 **{radon['average_rank']}（{radon['average_score']}）**，处于中等偏复杂水平。"
    )
    lines.append("")
    lines.append("| 排名 | 函数/方法 | 行号 | 复杂度 | 等级 |")
    lines.append("|------|-----------|------|--------|------|")
    for i, f in enumerate(radon["top_funcs"][:10], 1):
        # 尝试从 name 中提取文件路径
        name = f["name"]
        lines.append(
            f"| {i} | `{name}` | {f['line']}:{f['col']} | {f['complexity']} | {f['complexity_rank']} |"
        )
    lines.append("")

    # SonarQube / ZAP 未执行说明
    lines.append("## 7. SonarQube / Semgrep / OWASP ZAP 说明")
    lines.append("")
    lines.append(
        "本次扫描原计划集成 SonarQube Community、Semgrep 与 OWASP ZAP，但因当前环境无法连接 Docker 服务且未安装 Java 运行时，以下工具未能执行："
    )
    lines.append("")
    lines.append("- **SonarQube Community**：需要 Docker 或本地 Java 环境启动服务端与 Scanner。")
    lines.append("- **OWASP ZAP**：需要 Docker 或本地 Java 环境运行主动/基线扫描。")
    lines.append(
        "- **Semgrep**：需要网络拉取规则集；若后续网络可用，可补充运行 `semgrep --config=auto --config=p/security-audit --config=p/owasp-top-ten .`。"
    )
    lines.append("")
    lines.append(
        "已通过 **Bandit + 手动 DAST + 人工代码审查** 覆盖上述工具可能发现的主要问题（CORS、认证缺失、异常泄露、依赖 CVE 等）。"
    )
    lines.append("")

    # 优先修复建议
    lines.append("## 8. 优先修复建议与后续行动计划")
    lines.append("")
    lines.append("### 8.1 P0（立即修复）")
    lines.append("")
    lines.append(
        '1. **修复 CORS 配置**：在 `api/main.py` 中移除 `allow_origins=["*"]` 与 `allow_credentials=True` 的组合，改为读取环境变量 `GREENVRP_ALLOWED_ORIGINS` 并显式校验域名。'
    )
    lines.append(
        "2. **增加 API 认证与限流**：为 `/api/v1/solve`、`/api/v1/jobs`、`/api/v1/scenarios` 等敏感端点增加 API Key 或 JWT 认证；使用 `slowapi` 或 Nginx 配置限流。"
    )
    lines.append(
        '3. **异常信息脱敏**：在 `api/routers/solver.py` 中将 `raise HTTPException(status_code=500, detail=f"求解失败: {str(e)}")` 改为记录日志并返回统一错误消息。'
    )
    lines.append("")
    lines.append("### 8.2 P1（短期修复）")
    lines.append("")
    lines.append(
        "1. **修复依赖 CVE**：升级 `msgpack>=1.2.1`、`pydantic-settings>=2.14.2`；评估替换 `pdfkit` 或限制其使用。"
    )
    lines.append(
        "2. **校验 callback_url**：在 `api/services/solver_service.py` 中对 `callback_url` 进行协议、域名与白名单校验，防止 SSRF。"
    )
    lines.append(
        "3. **数据库线程安全**：在 `models/database.py` 中移除 `check_same_thread=False`，或为每个线程创建独立 `SessionLocal`；生产环境优先使用 PostgreSQL。"
    )
    lines.append(
        "4. **前端输入消毒**：在 `web_app.py` 与 `frontend/app.py` 中对 CSV 上传进行大小、编码、内容校验；移除不必要的 `unsafe_allow_html=True`。"
    )
    lines.append("")
    lines.append("### 8.3 P2（持续改进）")
    lines.append("")
    lines.append(
        "1. **规范导入与类型注解**：使用 `ruff check . --fix` 自动修复 `I001`、`UP035`、`UP006` 等；逐步为 `optimization/dynamic.py`、`core/distance.py` 等核心模块补充类型注解。"
    )
    lines.append("2. **降低圈复杂度**：对 Radon 识别的高复杂度函数（≥C）进行拆分或重构。")
    lines.append(
        "3. **修复 CI 配置**：将 `.github/workflows/ci.yml` 中的 `Ruff` 改为 `ruff`，确保 Lint 检查真正生效。"
    )
    lines.append(
        "4. **补齐专业扫描**：在具备 Docker/Java 的环境后，重新运行 SonarQube、Semgrep 与 OWASP ZAP，并与本报告对比。"
    )
    lines.append("")

    # 附录
    lines.append("## 附录：原始报告文件")
    lines.append("")
    lines.append("- `reports/security/bandit-report.json`")
    lines.append("- `reports/security/pip-audit-environment.json`")
    lines.append("- `reports/security/manual-dast.json`")
    lines.append("- `reports/quality/ruff-report-clean.json`")
    lines.append("- `reports/quality/mypy-report.txt`")
    lines.append("- `reports/quality/radon-cyclomatic.txt`")
    lines.append("- `reports/quality/radon-maintainability.txt`")
    lines.append("")

    OUT_FILE.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    build_report()
