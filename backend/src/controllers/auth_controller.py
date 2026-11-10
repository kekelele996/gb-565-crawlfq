"""认证 controller。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.constants.roles import role_permissions
from src.models.user import User
from src.services import audit_service, auth_service


def login(request: Request, db: Session, email: str, password: str) -> dict:
    user = auth_service.authenticate(db, email, password)
    db.commit()
    payload = auth_service.issue_token(user)
    audit_service.record(
        db,
        action="auth.login",
        entity_type="User",
        entity_id=user.id,
        actor=user,
        payload={"email": user.email, "role": user.role},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return payload


def me(user: User) -> dict:
    return {"user": auth_service.serialize_user(user)}


def capabilities(user: User) -> dict:
    return {
        "role": user.role,
        "permissions": role_permissions(user.role),
        "user": auth_service.serialize_user(user),
    }
