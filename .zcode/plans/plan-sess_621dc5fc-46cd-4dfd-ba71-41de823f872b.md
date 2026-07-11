## 测试体系全面打磨计划

### 现状
139个测试通过，30+模块零测试，2个测试文件因slowapi损坏

### 步骤
1. **修复slowapi**: test_routers和test_schemas恢复运行
2. **补纯函数测试**: data_types(6文件)、utils/validation、utils/time、utils/geo
3. **补优化模块**: carbon_aware(效率计算/场景对比)、multi_objective(帕累托/膝点)
4. **补核心可测部分**: solver(池/缓存)、database(get_db/init_db)
5. **覆盖率配置**: pytest-cov输出覆盖率摘要

### 预期
- 测试数139→220+
- 覆盖率~15%→~40%
- 新增7-10个测试文件