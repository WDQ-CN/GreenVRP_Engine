## GreenVRP Engine 项目开发初始化计划

### 目标
完成项目基础开发环境初始化，确保开发基线稳定可靠。

### 步骤

#### 步骤 1：初始化 Git 仓库
- 执行 `git init` 初始化版本控制
- 确认 `.gitignore` 已正确配置（排除 .venv、__pycache__、.idea、*.db 等）
- 创建首次提交，建立初始基线

#### 步骤 2：安装/验证依赖
- 确保 `.venv` 已激活
- 安装 `requirements.txt` 运行时依赖
- 安装 `requirements-test.txt` 测试依赖
- 验证关键包（ortools、fastapi、streamlit、sqlalchemy）可正常导入

#### 步骤 3：运行测试套件
- 执行 `pytest` 运行全部测试
- 记录测试结果，确保核心功能正常
- 如有失败，分析并记录问题

#### 步骤 4：数据库初始化检查
- 验证 `green_vrp.db` 表结构完整性
- 确认 `data/mock_customers.csv` 示例数据可加载

#### 步骤 5：代码质量检查
- 运行 `ruff check .` 检查代码风格
- 运行 `mypy .`（如果配置可用）

#### 步骤 6：验证启动入口
- 测试 `python start.py --help` 确认入口正常
- 快速验证 Web 界面可启动

### 所需权限
- Bash: 执行 git 命令
- Bash: 执行 pip 安装命令
- Bash: 执行 pytest、ruff、mypy 等检查命令
- Bash: 启动 Python 脚本验证