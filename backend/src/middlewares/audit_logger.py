"""ASGI 审计上下文中间件：trace_id、耗时、客户端 IP；业务审计由 service 显式落库。"""
from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.utils.logger import get_logger

logger = get_logger("crawlfq.access")
SKIP_PATHS = {"/health", "/api/health"}


class AuditContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex[:16]
        request.state.trace_id = trace_id
        request.state.client_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "")
        )
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        response.headers["x-trace-id"] = trace_id
        if request.url.path not in SKIP_PATHS:
            logger.info(
                "%s %s -> %s %sms trace=%s",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
                trace_id,
            )
        return response
