"""覆盖度审计 controller（含缺口 CSV 导出）。"""
from __future__ import annotations

from fastapi import Request, Response
from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.audit import AuditRunRequest
from src.services import coverage_service
from src.utils.timeutil import utcnow


def list_audits(db: Session) -> dict:
    return coverage_service.list_audits(db)


def get_audit(db: Session, audit_id: str) -> dict:
    return {"audit": coverage_service.get_audit(db, audit_id, include_gaps=True)}


def run_audit(request: Request, db: Session, user: User, payload: AuditRunRequest) -> dict:
    batch_label = payload.batch_label or f"manual-{utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    return coverage_service.run_audit(
        db,
        site_domain=payload.site_domain,
        batch_label=batch_label,
        actor=user,
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )


def gaps_csv(db: Session, audit_ids: list[str] | None = None) -> Response:
    content, rows = coverage_service.gaps_csv(db, audit_ids=audit_ids)
    headers = {"Content-Disposition": 'attachment; filename="crawlfq-coverage-gaps.csv"', "X-Row-Count": str(rows)}
    return Response(content="\ufeff" + content, media_type="text/csv; charset=utf-8", headers=headers)


def audit_gaps_csv(db: Session, audit_id: str) -> Response:
    return gaps_csv(db, audit_ids=[audit_id])
