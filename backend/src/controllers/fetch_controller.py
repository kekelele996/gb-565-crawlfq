"""抓取记录 controller。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import fetch_service


def list_fetches(
    db: Session,
    *,
    domain: str | None,
    status_code: int | None,
    origin: str | None,
    rate_limited: bool | None,
    page: int | None,
    page_size: int | None,
) -> dict:
    return fetch_service.list_fetches(
        db,
        domain=domain,
        status_code=status_code,
        origin=origin,
        rate_limited=rate_limited,
        page=page,
        page_size=page_size,
    )


def timeline(db: Session, limit: int = 60) -> dict:
    return fetch_service.timeline(db, limit=limit)
