## 测试体系重构计划

### 目标
对 GreenVRP Engine 建立高质量测试体系，确保覆盖核心逻辑、边缘用例和错误路径。

### 现状
- 51 个测试，仅覆盖 5/20+ 模块
- 零覆盖率：solver(942行)、API路由、安全认证、碳优化等
- 现有测试缺少参数化、Mock、强断言

### 阶段 0：测试基础设施增强
- conftest.py: 添加 TestClient、MockSolverService、内存DB fixture
- fixtures/customers.py: 添加多路线方案、Mock OR-Tools fixture
- 新增 tests/fixtures/mocks.py: MockSolver、MockJobManager、MockRedis

### 阶段 1：强化现有 5 个测试文件
- test_schemas.py: parametrize 边界值 + ScenarioCreate/Update + callback_url
- test_cost.py: 精确断言 + 多车型 + 缓存层测试
- test_distance.py: SparseDistanceMatrix + 极坐标 + scipy降级
- test_comparison.py: 参数化多场景 + 验证图表数据
- test_dynamic.py: _insert_customer/_remove_customer 实际路径

### 阶段 2：新增核心模块测试（最高优先级）
- core/solver.py: Mock OR-Tools，测验证/车队展开/自适应参数/解提取/实例池
- api/security/auth.py: API Key + JWT 认证全路径
- api/routers/solver.py: FastAPI TestClient 同步/异步/错误路径
- api/services/solver_service.py: 策略选择/任务生命周期/callback
- config/security.py: SSRF防护/URL校验/IP检测

### 阶段 3：新增中优先级测试
- optimization/carbon_aware.py: 三种优化方法/效率计算
- optimization/multi_objective.py: Pareto front/膝点检测
- data_types/*.py: 所有 dataclass 往返序列化
- utils/time.py + validation.py + geo.py

### 阶段 4：异常 + ORM 模型测试
- exceptions/errors.py: to_dict() 与 error_code
- models/database.py + ORM 模型

### 预期产出
- 新增 15-20 个测试文件，总数从 51 → 200+
- 覆盖率从 ~15% → ~60%+
- 全部使用 parametrize、Mock、精确断言

### 执行顺序
阶段 0 → 1 → 2 → 3 → 4，每阶段后全量测试确保无回归