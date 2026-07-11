# Tasks

- [ ] Task 1：Python 静态代码扫描
  - [ ] SubTask 1.1：运行 `python -m ruff check .` 并记录所有违规项
  - [ ] SubTask 1.2：运行 `bandit -r . -f json -o reports/bandit_scan.json`（如未安装则跳过并记录）
  - [ ] SubTask 1.3：运行 `python -m mypy . --ignore-missing-imports` 并记录类型错误
  - [ ] SubTask 1.4：按严重程度分类整理静态扫描结果

- [ ] Task 2：TypeScript/前端静态扫描
  - [ ] SubTask 2.1：在 `web/` 运行 `npm run lint` 并记录所有错误/警告
  - [ ] SubTask 2.2：在 `web/` 运行 `npx tsc -b` 并记录所有类型错误
  - [ ] SubTask 2.3：搜索 `console.log`/`console.error`/`debugger` 等未清理调试代码

- [ ] Task 3：测试全量执行与失败分析
  - [ ] SubTask 3.1：运行 `python -m pytest tests/ -v --tb=long` 并记录失败用例
  - [ ] SubTask 3.2：运行 `cd web && npm run test -- --run` 并记录失败用例
  - [ ] SubTask 3.3：检查是否存在端到端/集成测试脚本并执行

- [ ] Task 4：依赖安全与兼容性审计
  - [ ] SubTask 4.1：运行 `python -m pip_audit` 或 `pip-audit` 扫描 Python 依赖 CVE
  - [ ] SubTask 4.2：运行 `cd web && npm audit` 扫描前端依赖 CVE
  - [ ] SubTask 4.3：检查 Python/Node 版本兼容性与依赖冲突

- [ ] Task 5：关键功能手动边界测试
  - [ ] SubTask 5.1：启动 API（设置测试 API Key），测试认证/未认证/错误 Key/空 Key 场景
  - [ ] SubTask 5.2：测试求解接口边界：0 客户、1 客户、超大客户数、非法坐标、缺失字段
  - [ ] SubTask 5.3：测试场景 CRUD 与 CSV 上传边界
  - [ ] SubTask 5.4：测试 callback_url SSRF 边界（私有 IP、localhost、非法协议）

- [ ] Task 6：运行时异常与日志分析
  - [ ] SubTask 6.1：扫描项目目录中的 `.log` 文件与 `logs/` 目录
  - [ ] SubTask 6.2：汇总近期命令输出中的 `stderr` 与未处理异常堆栈
  - [ ] SubTask 6.3：识别重复出现的异常模式与高频率警告

- [ ] Task 7：生成 BUG 报告
  - [ ] SubTask 7.1：汇总 Task 1~6 的所有发现
  - [ ] SubTask 7.2：按严重程度（Critical/High/Medium/Low）分类
  - [ ] SubTask 7.3：为每个问题填写描述、复现步骤、影响范围、初步定位
  - [ ] SubTask 7.4：生成 `reports/GreenVRP_Bug_Scan_Report.md`
  - [ ] SubTask 7.5：再次运行 lint/test/build 确认扫描过程未破坏项目

# Task Dependencies

- Task 7 依赖 Task 1 ~ Task 6
- Task 1 与 Task 2 可并行
- Task 3 与 Task 4 可并行
- Task 5 与 Task 6 可并行
