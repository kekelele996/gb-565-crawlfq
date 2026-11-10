"""写接口限流（Redis 滑动窗口，按 token 用户或客户端 IP），超限 429。

只拦 POST/PATCH/PUT/DELETE，读取接口不限流；Redis 不可用时降级放行。
"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.config.settings import settings
from src.constants import error_codes as codes
from src.utils.jwt import TokenError, decode_token
from src.utils.logger import get_logger
from src.utils.redis_client import get_redis

logger = get_logger("crawlfq.ratelimit")
WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


def _identity(request: Request) -> str:
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        try:
            payload = decode_token(header.split(" ", 1)[1].strip())
            if payload.get("sub"):
                return f"user:{payload['sub']}"
        except TokenError:
            pass
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return f"ip:{forwarded or (request.client.host if request.client else 'unknown')}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in WRITE_METHODS or request.url.path in ("/health", "/api/health"):
            return await call_next(request)
        limit = settings.rate_limit_write_per_minute
        key = f"crawlfq:ratelimit:write:{_identity(request)}"
        try:
            client = get_redis()
            now = time.time()
            pipeline = client.pipeline()
            pipeline.zremrangebyscore(key, 0, now - 60)
            pipeline.zadd(key, {f"{now}": now})
            pipeline.zcard(key)
            pipeline.expire(key, 90)
            results = pipeline.execute()
            count = int(results[2])
        except Exception:  # noqa: BLE001 - Redis 不稳定时限流降级，不应让服务不可用
            return await call_next(request)
        if count > limit:
            return JSONResponse(
                status_code=429,
                content={
                    "code": codes.RATE_LIMITED,
                    "message": "写操作过于频繁，请稍后重试",
                    "detail": f"count={count} limit={limit}/min",
                    "trace_id": getattr(request.state, "trace_id", None),
                },
            )
        return await call_next(request)
