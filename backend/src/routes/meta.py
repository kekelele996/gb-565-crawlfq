"""元信息路由：健康检查公开；总览与审计日志受权限控制。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import meta_controller
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health(db: Session = Depends(get_db)):
    return meta_controller.health(db)


@router.get("/meta/overview")
async def overview(db: Session = Depends(get_db), user: User = require_permission("frontier:read")):
    return meta_controller.overview(db)


@router.get("/meta/audit-logs")
async def audit_logs(
    db: Session = Depends(get_db),
    user: User = require_permission("audit:read"),
    limit: int = 50,
):
    return meta_controller.audit_logs(db, limit=min(max(limit, 1), 200))
