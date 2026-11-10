"""URL 前沿 controller。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.schemas.frontier import FrontierPreviewRequest
from src.services import frontier_service


def list_urls(
    db: Session,
    *,
    domain: str | None,
    status: str | None,
    duplicate: str | None,
    q: str | None,
    page: int | None,
    page_size: int | None,
) -> dict:
    return frontier_service.list_urls(
        db,
        domain=domain,
        status=status,
        duplicate=duplicate,
        q=q,
        page=page,
        page_size=page_size,
    )


def stats(db: Session) -> dict:
    return frontier_service.stats(db)


def examples(db: Session, limit: int = 3) -> dict:
    return {"items": frontier_service.examples(db, limit=limit)}


def preview(db: Session, payload: FrontierPreviewRequest) -> dict:
    return frontier_service.preview(db, payload.url)
