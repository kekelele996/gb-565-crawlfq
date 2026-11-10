"""认证：Bearer -> request.state.user（每次请求回查 DB 的角色）。

白名单由路由显式声明：登录 / 健康检查不需要 token。
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants import error_codes as codes
from src.models.user import User
from src.utils.errors import AppError
from src.utils.jwt import TokenError, decode_token


def _extract_bearer(request: Request) -> str | None:
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        return None
    return header.split(" ", 1)[1].strip()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _extract_bearer(request)
    if not token:
        raise AppError(codes.AUTH_REQUIRED, "请先登录", "missing Authorization header")
    try:
        payload = decode_token(token)
    except TokenError as exc:
        raise AppError(codes.AUTH_INVALID, "登录已过期，请重新登录", str(exc)) from exc
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise AppError(codes.AUTH_INVALID, "登录状态无效，请重新登录", "user missing/inactive")
    request.state.user = user
    return user


def request_meta(request: Request) -> dict[str, Any]:
    return {
        "ip": getattr(request.state, "client_ip", None),
        "trace_id": getattr(request.state, "trace_id", None),
    }
