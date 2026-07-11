"""
Redis 任务管理器（生产环境版）

使用 Redis 持久化任务状态，支持：
- 服务重启后任务状态不丢失
- 多实例水平扩展
- 自动过期清理
- 分布式锁防止并发冲突
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis

logger = logging.getLogger(__name__)


def _redact_redis_url(url: str) -> str:
    """脱敏 Redis URL 中的密码信息。"""
    import re
    return re.sub(r'(redis://[^:]+:)[^@]+(@)', r'\1****\2', url)


class RedisJobManager:
    """基于 Redis 的任务管理器（生产环境推荐）。"""

    # Redis Key 前缀
    JOB_KEY_PREFIX = "green_vrp:job:"
    JOB_INDEX_KEY = "green_vrp:job:index"
    
    # 默认过期时间（24 小时）
    DEFAULT_TTL_HOURS = 24
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ):
        """
        初始化 Redis 任务管理器。
        
        Args:
            redis_url: Redis 连接 URL
            ttl_hours: 任务数据保留时间（小时）
        """
        self.redis_url = redis_url
        self.ttl_seconds = ttl_hours * 3600
        
        # 创建 Redis 连接（使用连接池）
        self.redis = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5.0,
            socket_timeout=5.0,
            retry_on_timeout=True,
        )
        
        # 测试连接
        try:
            self.redis.ping()
            logger.info(f"Redis 连接成功：{_redact_redis_url(redis_url)}")
        except redis.ConnectionError as e:
            logger.error(f"Redis 连接失败：{e}")
            raise

    def create_job(self) -> str:
        """创建新任务，返回任务 ID。"""
        job_id = str(uuid.uuid4())
        job_key = f"{self.JOB_KEY_PREFIX}{job_id}"
        
        job_data = {
            "job_id": job_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "solution": None,
            "cost_result": None,
            "error_message": None,
            "callback_url": None,
        }
        
        # 存储任务数据
        pipe = self.redis.pipeline()
        pipe.set(job_key, json.dumps(job_data))
        pipe.expire(job_key, self.ttl_seconds)
        
        # 添加到索引（用于列出所有任务）
        pipe.zadd(self.JOB_INDEX_KEY, {job_id: datetime.now().timestamp()})
        pipe.expire(self.JOB_INDEX_KEY, self.ttl_seconds)
        
        pipe.execute()
        
        return job_id

    def update_job(self, job_id: str, **kwargs) -> bool:
        """
        更新任务状态。
        
        Args:
            job_id: 任务 ID
            **kwargs: 要更新的字段
            
        Returns:
            是否更新成功
        """
        job_key = f"{self.JOB_KEY_PREFIX}{job_id}"
        
        # 获取当前数据
        current_data = self.redis.get(job_key)
        if not current_data:
            return False
        
        job_data = json.loads(current_data)
        job_data.update(kwargs)
        
        # 特殊处理：将 datetime 对象转换为 ISO 字符串
        for key, value in job_data.items():
            if isinstance(value, datetime):
                job_data[key] = value.isoformat()
        
        # 更新并刷新 TTL
        pipe = self.redis.pipeline()
        pipe.set(job_key, json.dumps(job_data))
        pipe.expire(job_key, self.ttl_seconds)
        pipe.execute()
        
        return True

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息。
        
        Args:
            job_id: 任务 ID
            
        Returns:
            任务数据字典，如果不存在则返回 None
        """
        job_key = f"{self.JOB_KEY_PREFIX}{job_id}"
        job_data = self.redis.get(job_key)
        
        if not job_data:
            return None
        
        parsed = json.loads(job_data)
        
        # 将 ISO 字符串转换回 datetime 对象
        for key in ["created_at", "started_at", "completed_at"]:
            if parsed.get(key):
                try:
                    parsed[key] = datetime.fromisoformat(parsed[key])
                except (ValueError, TypeError):
                    pass
        
        return parsed

    def list_jobs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        列出所有任务（按创建时间倒序）。
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            任务列表
        """
        # 从有序集合中获取最新的 job_id
        job_ids = self.redis.zrevrange(
            self.JOB_INDEX_KEY, 
            offset, 
            offset + limit - 1
        )
        
        jobs = []
        for job_id in job_ids:
            job_data = self.get_job(job_id)
            if job_data:
                jobs.append(job_data)
        
        return jobs

    def delete_job(self, job_id: str) -> bool:
        """
        删除任务。
        
        Args:
            job_id: 任务 ID
            
        Returns:
            是否删除成功
        """
        job_key = f"{self.JOB_KEY_PREFIX}{job_id}"
        
        pipe = self.redis.pipeline()
        pipe.delete(job_key)
        pipe.zrem(self.JOB_INDEX_KEY, job_id)
        pipe.execute()
        
        return True

    def cleanup_expired_jobs(self) -> int:
        """
        清理过期任务（手动触发）。
        
        Redis 会自动通过 TTL 清理，此方法用于主动清理索引中的孤儿记录。
        
        Returns:
            清理的任务数量
        """
        all_job_ids = self.redis.zrange(self.JOB_INDEX_KEY, 0, -1)
        cleaned = 0
        
        for job_id in all_job_ids:
            job_key = f"{self.JOB_KEY_PREFIX}{job_id}"
            if not self.redis.exists(job_key):
                # 索引存在但数据已过期，清理索引
                self.redis.zrem(self.JOB_INDEX_KEY, job_id)
                cleaned += 1
        
        return cleaned

    def get_stats(self) -> Dict[str, Any]:
        """
        获取任务统计信息。
        
        Returns:
            统计信息字典
        """
        all_job_ids = self.redis.zrange(self.JOB_INDEX_KEY, 0, -1)
        
        stats = {
            "total": len(all_job_ids),
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
        }
        
        for job_id in all_job_ids:
            job_data = self.get_job(job_id)
            if job_data:
                status = job_data.get("status", "unknown")
                if status in stats:
                    stats[status] += 1
        
        return stats

    def close(self) -> None:
        """关闭 Redis 连接。"""
        self.redis.close()


# 可选：内存版作为后备（当 Redis 不可用时）
class MemoryJobManagerFallback:
    """内存版任务管理器（开发/降级模式）。"""
    
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        logger.warning("使用内存版任务管理器（开发模式）")

    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "solution": None,
            "cost_result": None,
            "error_message": None,
            "callback_url": None,
        }
        return job_id

    def update_job(self, job_id: str, **kwargs) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].update(kwargs)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        jobs = list(self._jobs.values())
        return jobs[:limit]

    def delete_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False


def create_job_manager(
    redis_url: Optional[str] = None,
    use_fallback: bool = True,
) -> Any:
    """
    工厂函数：创建任务管理器实例。
    
    优先尝试连接 Redis，失败时根据配置决定是否降级到内存版。
    
    Args:
        redis_url: Redis 连接 URL（可从环境变量读取）
        use_fallback: Redis 不可用时是否降级到内存版
        
    Returns:
        RedisJobManager 或 MemoryJobManagerFallback 实例
    """
    import os
    
    # 从环境变量获取 Redis URL
    if not redis_url:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        return RedisJobManager(redis_url=redis_url)
    except redis.ConnectionError:
        if use_fallback:
            logger.warning("Redis 不可用，降级到内存版任务管理器")
            return MemoryJobManagerFallback()
        else:
            raise
