"""URL 前沿路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import frontier_controller
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.frontier import FrontierPreviewRequest

router = APIRouter(prefix="/frontier", tags=["frontier"])


@router.get("")
async def list_urls(
    db: Session = Depends(get_db),
    user: User = require_permission("frontier:read"),
    domain: str | None = None,
    status: str | None = None,
    duplicate: str | None = Query(None, pattern="^(only|exclude)$"),
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    return frontier_controller.list_urls(
        db,
        domain=domain,
        status=status,
        duplicate=duplicate,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.get("/stats")
async def stats(db: Session = Depends(get_db), user: User = require_permission("frontier:read")):
    return frontier_controller.stats(db)


@router.get("/examples")
async def examples(
    db: Session = Depends(get_db),
    user: User = require_permission("frontier:read"),
    limit: int = 3,
):
    return frontier_controller.examples(db, limit=min(max(limit, 1), 6))


@router.post("/preview")
async def preview(
    payload: FrontierPreviewRequest,
    db: Session = Depends(get_db),
    user: User = require_permission("frontier:preview"),
):
    return frontier_controller.preview(db, payload)
