# 任务管理器升级指南

## 概述

已将内存版 `JobManager` 升级为支持 Redis 的生产级任务管理器，实现：
- ✅ 服务重启后任务状态不丢失
- ✅ 多实例水平扩展
- ✅ 自动过期清理（默认 24 小时）
- ✅ 降级模式（Redis 不可用时自动切换到内存版）

---

## 文件变更

### 新增文件
- `api/services/redis_job_manager.py` - Redis 任务管理器实现

### 修改文件
- `api/services/solver_service.py` - 集成 Redis 任务管理器
- `api/services/__init__.py` - 导出新组件
- `requirements.txt` - 添加 redis 依赖

---

## 部署步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

或单独安装：
```bash
pip install redis>=4.5.0
```

### 2. 启动 Redis 服务器

#### Docker 方式（推荐）
```bash
docker run -d --name green-vrp-redis \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:7-alpine
```

#### Systemd 方式
```bash
sudo apt-get install redis-server  # Ubuntu/Debian
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 3. 配置环境变量

在生产环境中设置 `REDIS_URL`：

```bash
# .env 文件或环境变量
REDIS_URL=redis://localhost:6379/0
```

或使用带认证的连接：
```bash
REDIS_URL=redis://:your_password@localhost:6379/0
```

### 4. 验证部署

```python
from api.services import job_manager

# 检查是否连接到 Redis
print(type(job_manager))  
# 成功连接：<class 'api.services.redis_job_manager.RedisJobManager'>
# 降级模式：<class 'api.services.redis_job_manager.MemoryJobManagerFallback'>
```

---

## 使用示例

### 创建异步任务

```python
from api.services import solver_service

# 提交异步求解任务
job_id = await solver_service.solve_async(
    customers=customer_list,
    vehicle_config=config,
    params={"time_limit": 60},
    callback_url="https://your-api.com/webhook"
)

print(f"任务已提交：{job_id}")
```

### 查询任务状态

```python
from api.services import solver_service

job_status = solver_service.get_job_status(job_id)

if job_status["status"] == "completed":
    solution = job_status["solution"]
    cost = job_status["cost_result"]
elif job_status["status"] == "failed":
    error = job_status["error_message"]
```

### 列出所有任务

```python
from api.services import job_manager

# 获取最近 100 个任务
jobs = job_manager.list_jobs(limit=100)

for job in jobs:
    print(f"{job['job_id'][:8]}... - {job['status']}")
```

### 获取统计信息（仅 Redis 版）

```python
if hasattr(job_manager, 'get_stats'):
    stats = job_manager.get_stats()
    print(f"总任务数：{stats['total']}")
    print(f"进行中：{stats['processing']}")
    print(f"已完成：{stats['completed']}")
    print(f"失败：{stats['failed']}")
```

---

## 高级配置

### 调整 TTL（任务保留时间）

```python
from api.services.redis_job_manager import RedisJobManager

# 设置为 48 小时
job_manager = RedisJobManager(ttl_hours=48)
```

### 自定义 Redis 连接参数

```python
from api.services.redis_job_manager import RedisJobManager

job_manager = RedisJobManager(
    redis_url="redis://localhost:6379/0",
    ttl_hours=24,
)

# 底层 Redis 客户端支持更多配置
job_manager.redis.config_set("maxmemory", "256mb")
```

### 手动清理过期任务

```python
# Redis 会自动通过 TTL 清理，但也可以手动触发
cleaned_count = job_manager.cleanup_expired_jobs()
print(f"清理了 {cleaned_count} 个过期任务")
```

### 删除单个任务

```python
success = job_manager.delete_job(job_id)
```

---

## 降级模式说明

当 Redis 不可用时，系统会自动降级到内存版任务管理器：

```
✗ Redis 连接失败：Error 111 connecting to localhost:6379. Connection refused.
⚠ Redis 不可用，降级到内存版任务管理器
⚠ 使用内存版任务管理器（开发模式）
```

**注意**：降级模式下，服务重启会导致所有任务状态丢失。建议仅用于开发环境。

---

## 生产环境最佳实践

### 1. Redis 高可用

使用 Redis Sentinel 或 Redis Cluster：

```bash
# Sentinel 配置示例
REDIS_URL=redis://sentinel1:26379,sentinel2:26379,sentinel3:26379/0
```

### 2. 监控告警

监控 Redis 连接状态和任务队列长度：

```python
# 健康检查端点示例
@app.get("/health/jobs")
async def job_health():
    stats = job_manager.get_stats()
    if stats["total"] > 1000:
        return {"status": "warning", "message": "任务队列过长"}
    return {"status": "healthy", **stats}
```

### 3. 日志记录

建议添加任务状态变更日志：

```python
import logging

logger = logging.getLogger(__name__)

def log_job_transition(job_id, old_status, new_status):
    logger.info(f"任务 {job_id[:8]}... 从 {old_status} 变更为 {new_status}")
```

### 4. 数据持久化

对于关键任务，建议将结果保存到数据库：

```python
# 在回调中添加数据库保存逻辑
if job_status == "completed":
    db_solution = Solution(
        job_id=job_id,
        solution_data=json.dumps(solution),
        created_at=datetime.now()
    )
    db.add(db_solution)
    db.commit()
```

---

## 故障排查

### Redis 连接失败

```bash
# 检查 Redis 是否运行
redis-cli ping
# 应返回：PONG

# 查看 Redis 日志
docker logs green-vrp-redis
# 或
sudo journalctl -u redis-server
```

### 任务状态不一致

```python
# 手动清理索引中的孤儿记录
cleaned = job_manager.cleanup_expired_jobs()
print(f"清理了 {cleaned} 个不一致的任务")
```

### 内存占用过高

```python
# 检查 Redis 内存使用
info = job_manager.redis.info("memory")
print(f"已用内存：{info['used_memory_human']}")

# 缩短 TTL 或增加清理频率
```

---

## 性能对比

| 特性 | 内存版 | Redis 版 |
|------|--------|----------|
| 重启后数据保留 | ❌ | ✅ |
| 水平扩展 | ❌ | ✅ |
| 并发能力 | 低 | 高 |
| 内存占用 | 进程内 | 独立服务 |
| 适用场景 | 开发/测试 | 生产环境 |

---

## 回滚方案

如需回滚到纯内存版：

```python
# 在 solver_service.py 中改回：
from .solver_service import JobManager
job_manager = JobManager()
```

并移除 Redis 相关依赖。
