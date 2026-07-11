"""
GreenVRP Engine FastAPI 应用入口

提供 REST API 服务，支持：
- 同步/异步求解
- 场景管理
- 健康检查

启动方式：
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

API 文档：
    http://localhost:8000/docs (Swagger UI)
    http://localhost:8000/redoc (ReDoc)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import health_router, scenarios_router, solver_router
from .security.auth import get_current_user
from .security.rate_limit import limiter, setup_rate_limiting
from config.security import security_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 启动时初始化
    print("GreenVRP Engine API 启动中...")
    yield
    # 关闭时清理
    print("GreenVRP Engine API 关闭中...")


# 创建 FastAPI 应用
app = FastAPI(
    title="绿色物流路径优化引擎 API",
    description="""
## 绿色物流路径优化引擎 API

基于异构车队与软时间窗的城市配送碳排与成本优化系统。

### 主要功能

- **求解器**: VRPTW 问题求解，支持同步/异步模式
- **场景管理**: 场景数据的增删改查
- **成本核算**: 五维成本模型（运输、人工、固定、惩罚、碳排）

### 使用流程

1. 创建场景或直接提交求解请求
2. 同步求解等待结果，或异步求解后轮询状态
3. 获取求解结果和成本分析
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 配置 - 限制为允许的来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=security_config.ALLOWED_ORIGINS,  # 从安全配置加载
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# 设置速率限制
setup_rate_limiting(app)

# 注册路由
app.include_router(health_router, prefix="/api/v1", tags=["系统"])
app.include_router(solver_router, prefix="/api/v1", tags=["求解器"])
app.include_router(scenarios_router, prefix="/api/v1", tags=["场景管理"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
