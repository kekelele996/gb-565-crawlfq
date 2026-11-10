"""审计日志服务：业务动作成功后显式落库（带 trace_id / IP）。"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog
from src.models.user import User
from src.utils.timeutil import to_iso


def record(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: object = "",
    actor: User | None = None,
    payload: dict | None = None,
    ip: str | None = None,
    trace_id: str | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id or ""),
            actor_email=actor.email if actor else "",
            actor_role=actor.role if actor else "",
            payload=json.dumps(payload or {}, ensure_ascii=False),
            ip=(ip or "")[:64],
            trace_id=(trace_id or "")[:64],
        )
    )
    db.commit()


def serialize_log(log: AuditLog) -> dict:
    try:
        payload = json.loads(log.payload or "{}")
    except ValueError:
        payload = {}
    return {
        "id": str(log.id),
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "actor_email": log.actor_email,
        "actor_role": log.actor_role,
        "payload": payload,
        "ip": log.ip,
        "trace_id": log.trace_id,
        "created_at": to_iso(log.created_at),
    }


def list_logs(db: Session, limit: int = 50) -> list[dict]:
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [serialize_log(row) for row in rows]
