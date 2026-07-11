"""
GreenVRP Engine FastAPI 应用入口

提供 REST API 服务，支持：
- 同步/异步求解
- 场景管理
- 健康检查

启动方式：
    uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

API 文档：
    http://localhost:8000/docs (Swagger UI)
    http://localhost:8000/redoc (ReDoc)
"""

import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import Message

from config.settings import Settings
from exceptions.errors import (
    ConfigurationError,
    GreenVRPError,
    JobNotFoundError,
    JobTimeoutError,
    ServiceUnavailableError,
    ValidationError,
)
from models.database import init_db

from .middleware.security import APIKeyAuthMiddleware, RateLimitMiddleware
from .routers import health_router, jobs_router, scenarios_router, solver_router

logger = logging.getLogger(__name__)

# 默认最大请求体大小：10 MB
DEFAULT_MAX_REQUEST_SIZE = 10 * 1024 * 1024


class ContentSizeLimitMiddleware:
    """
    请求体大小限制中间件。

    通过 Content-Length 头或实际读取的字节数限制请求体大小，
    超过限制时返回 HTTP 413，避免 oversized payload 进入业务逻辑。
    """

    def __init__(self, app, max_size_bytes: int = DEFAULT_MAX_REQUEST_SIZE):
        self.app = app
        self.max_size_bytes = max_size_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = 0
        headers = dict(scope.get("headers", []))
        content_length_header = headers.get(b"content-length")
        if content_length_header:
            try:
                content_length = int(content_length_header.decode("ascii"))
            except (ValueError, UnicodeDecodeError):
                await self._reject(send, 400, "Invalid Content-Length header")
                return

            if content_length > self.max_size_bytes:
                await self._reject(
                    send,
                    413,
                    f"Request body too large: {content_length} > {self.max_size_bytes}",
                )
                return

        # 对未声明 Content-Length 的分块请求，通过包装 receive 计数兜底
        bytes_read = 0

        async def capped_receive() -> Message:
            nonlocal bytes_read
            message = await receive()
            if message.get("type") == "http.request":
                chunk = message.get("body", b"")
                bytes_read += len(chunk)
                if bytes_read > self.max_size_bytes:
                    await self._reject(
                        send,
                        413,
                        f"Request body too large: exceeded {self.max_size_bytes} bytes",
                    )
                    # 返回空消息以终止后续读取；中间件已发送响应
                    return {"type": "http.request", "body": b""}
            return message

        await self.app(scope, capped_receive, send)

    @staticmethod
    async def _reject(send, status_code: int, detail: str):
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        # 使用 json.dumps 避免 detail 中包含引号等特殊字符时破坏 JSON 结构
        body = json.dumps({"detail": detail}, ensure_ascii=False).encode("utf-8")
        await send({"type": "http.response.body", "body": body})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 启动时初始化数据库表
    logger.info("GreenVRP Engine API 启动中...")
    init_db()
    logger.info("数据库表初始化完成")
    yield
    # 关闭时清理
    logger.info("GreenVRP Engine API 关闭中...")
    # 优雅关闭 SolverService 单例，取消或等待后台任务
    from api.dependencies import _solver_service

    if _solver_service is not None and hasattr(_solver_service, "close"):
        await _solver_service.close()


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

# CORS 配置：生产环境必须显式配置受信任域名，禁止 * 与 allow_credentials=True 同时使用
settings = Settings.from_env()
allow_credentials = os.getenv("GREENVRP_ALLOW_CREDENTIALS", "true").lower() == "true"
origins = settings.allowed_origins
if "*" in origins:
    if allow_credentials:
        raise ValueError("CORS 配置冲突：allow_credentials=True 时 allow_origins 不能包含 '*'")
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-API-Key"],
)

# 安全中间件。按 Starlette 执行规则，后添加的中间件先处理请求；
# 因此先添加 APIKeyAuth，再添加 RateLimit，实际请求顺序为 RateLimit -> APIKeyAuth -> CORS。
app.add_middleware(APIKeyAuthMiddleware)
app.add_middleware(RateLimitMiddleware)

# 请求体大小限制中间件。最后添加，最先执行，避免 oversized payload 进入后续中间件与路由。
_max_request_size = int(os.getenv("GREENVRP_MAX_REQUEST_SIZE", str(DEFAULT_MAX_REQUEST_SIZE)))
app.add_middleware(ContentSizeLimitMiddleware, max_size_bytes=_max_request_size)


def _resolve_greenvrp_status_code(exc: GreenVRPError) -> int:
    """根据异常类型映射合适的 HTTP 状态码。"""
    match exc:
        case JobNotFoundError():
            return 404
        case ValidationError():
            return 422
        case ConfigurationError():
            return 500
        case JobTimeoutError():
            return 504
        case ServiceUnavailableError():
            return 503
        case _:
            return 400


@app.exception_handler(GreenVRPError)
async def greenvrp_error_handler(request: Request, exc: GreenVRPError):
    status_code = _resolve_greenvrp_status_code(exc)
    logger.warning(
        "业务异常: path=%s, status=%d, error_code=%s, message=%s",
        request.url.path,
        status_code,
        exc.error_code,
        exc.message,
    )
    return JSONResponse(status_code=status_code, content=exc.to_dict())


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局未捕获异常处理器。

    向客户端返回脱敏的通用错误消息，服务端记录完整 traceback 以便排查。
    """
    request_path = request.url.path if request.url else "unknown"
    logger.exception(
        "未捕获的异常: path=%s, exc_type=%s",
        request_path,
        type(exc).__name__,
    )
    # 完整 traceback 已由 logger.exception 记录，无需再手动拼接
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# 注册路由
app.include_router(health_router, prefix="/api/v1", tags=["系统"])
app.include_router(solver_router, prefix="/api/v1", tags=["求解器"])
app.include_router(jobs_router, prefix="/api/v1", tags=["任务管理"])
app.include_router(scenarios_router, prefix="/api/v1", tags=["场景管理"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
