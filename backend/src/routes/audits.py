"""覆盖度审计路由（注意：静态路径 /gaps.csv 声明在 /{audit_id} 之前）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import audit_controller
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.audit import AuditRunRequest

router = APIRouter(prefix="/audits", tags=["audits"])


@router.get("")
async def list_audits(db: Session = Depends(get_db), user: User = require_permission("audits:read")):
    return audit_controller.list_audits(db)


@router.get("/gaps.csv")
async def all_gaps_csv(db: Session = Depends(get_db), user: User = require_permission("audits:export")):
    return audit_controller.gaps_csv(db)


@router.post("/run")
async def run_audit(
    request: Request,
    payload: AuditRunRequest,
    db: Session = Depends(get_db),
    user: User = require_permission("audits:run"),
):
    return audit_controller.run_audit(request, db, user, payload)


@router.get("/{audit_id}")
async def get_audit(audit_id: str, db: Session = Depends(get_db), user: User = require_permission("audits:read")):
    return audit_controller.get_audit(db, audit_id)


@router.get("/{audit_id}/gaps.csv")
async def audit_gaps_csv(
    audit_id: str, db: Session = Depends(get_db), user: User = require_permission("audits:export")
):
    return audit_controller.audit_gaps_csv(db, audit_id)
