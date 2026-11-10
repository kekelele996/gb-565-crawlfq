"""抓取记录与时间线路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import fetch_controller
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(prefix="/fetches", tags=["fetches"])


@router.get("")
async def list_fetches(
    db: Session = Depends(get_db),
    user: User = require_permission("fetches:read"),
    domain: str | None = None,
    status_code: int | None = None,
    origin: str | None = None,
    rate_limited: bool | None = None,
    page: int = 1,
    page_size: int = 20,
):
    return fetch_controller.list_fetches(
        db,
        domain=domain,
        status_code=status_code,
        origin=origin,
        rate_limited=rate_limited,
        page=page,
        page_size=page_size,
    )


@router.get("/timeline")
async def timeline(
    db: Session = Depends(get_db),
    user: User = require_permission("fetches:read"),
    limit: int = 60,
):
    return fetch_controller.timeline(db, limit=min(max(limit, 5), 120))
