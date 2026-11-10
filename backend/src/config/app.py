"""FastAPI 应用装配：中间件顺序、异常处理、路由挂载、启动钩子（建表 + seed）。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.database import init_db
from src.config.settings import settings
from src.middlewares.audit_logger import AuditContextMiddleware
from src.middlewares.error_handler import register_exception_handlers
from src.middlewares.rate_limit import RateLimitMiddleware
from src.routes import api_router
from src.services import frontier_service
from src.utils.logger import log_event

logger = logging.getLogger("crawlfq.app")


def _bootstrap() -> None:
    init_db()
    if not settings.seed_demo:
        return
    try:
        from scripts.seed_demo import seed_all

        result = seed_all()
        log_event("SEED_DEMO_FINISHED", **result)
    except Exception as exc:  # noqa: BLE001 - seed 失败不能阻塞服务启动
        logger.warning("[SEED_DEMO] failed (ignored): %s: %s", type(exc).__name__, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _bootstrap()
    frontier_service.reset_index()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="crawlfq · 采集前沿调度与礼貌配额管制台",
        description="澜舟情报爬虫组：URL 规范化去重 + 域配额令牌桶调度 + sitemap 覆盖度审计",
        version="1.0.0",
        lifespan=lifespan,
    )

    register_exception_handlers(app)
    # added first => innermost
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuditContextMiddleware)
    # added last => outermost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Trace-ID", "X-Row-Count"],
    )

    # 同一份路由挂两次：/api/* 给直连；根路径给 Nginx 剥掉 /api 后的反代
    app.include_router(api_router, prefix="/api")
    app.include_router(api_router, include_in_schema=False)
    return app


app = create_app()
