"""站点 controller。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.site import SiteUpdateRequest
from src.services import site_service


def list_sites(db: Session) -> dict:
    return site_service.list_sites(db)


def get_site(db: Session, site_id: str) -> dict:
    return {"site": site_service.serialize_site(site_service.get_site(db, site_id))}


def update_site(request: Request, db: Session, user: User, site_id: str, payload: SiteUpdateRequest) -> dict:
    return site_service.update_site(
        db,
        site_id,
        payload.model_dump(exclude_unset=True),
        actor=user,
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
