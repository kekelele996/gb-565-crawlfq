"""抓取记录与限速事件时间线服务。"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.fetch_record import FetchRecord
from src.utils.pagination import normalize_pagination
from src.utils.timeutil import to_iso


def serialize_fetch(row: FetchRecord) -> dict:
    return {
        "id": str(row.id),
        "task_id": str(row.task_id) if row.task_id else None,
        "domain": row.domain,
        "status_code": row.status_code,
        "latency_ms": row.latency_ms,
        "bytes": row.bytes,
        "was_duplicate": row.was_duplicate,
        "rate_limited": row.rate_limited,
        "backoff_applied_s": row.backoff_applied_s,
        "origin": row.origin,
        "fetched_at": to_iso(row.fetched_at),
    }


def list_fetches(
    db: Session,
    *,
    domain: str | None = None,
    status_code: int | None = None,
    origin: str | None = None,
    rate_limited: bool | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> dict:
    page, page_size = normalize_pagination(page, page_size)
    query = db.query(FetchRecord)
    if domain:
        query = query.filter(FetchRecord.domain == domain)
    if status_code:
        query = query.filter(FetchRecord.status_code == status_code)
    if origin:
        query = query.filter(FetchRecord.origin == origin)
    if rate_limited is not None:
        query = query.filter(FetchRecord.rate_limited.is_(rate_limited))
    total = query.count()
    rows = (
        query.order_by(FetchRecord.fetched_at.desc(), FetchRecord.domain.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    summary_rows = (
        db.query(FetchRecord.status_code, func.count(FetchRecord.id)).group_by(FetchRecord.status_code).all()
    )
    summary = {
        "total": db.query(func.count(FetchRecord.id)).scalar() or 0,
        "rate_limited": db.query(func.count(FetchRecord.id))
        .filter(FetchRecord.rate_limited.is_(True))
        .scalar()
        or 0,
        "duplicates": db.query(func.count(FetchRecord.id))
        .filter(FetchRecord.was_duplicate.is_(True))
        .scalar()
        or 0,
        "by_status": {str(code): int(count) for code, count in summary_rows},
        "by_origin": {},
    }
    origin_rows = db.query(FetchRecord.origin, func.count(FetchRecord.id)).group_by(FetchRecord.origin).all()
    summary["by_origin"] = {origin_name: int(count) for origin_name, count in origin_rows}
    return {"items": [serialize_fetch(row) for row in rows], "total": total, "page": page, "page_size": page_size, "summary": summary}


def timeline(db: Session, limit: int = 60) -> dict:
    rows = (
        db.query(FetchRecord)
        .order_by(FetchRecord.fetched_at.desc(), FetchRecord.domain.asc())
        .limit(limit)
        .all()
    )
    events = [
        {
            **serialize_fetch(row),
            "signal": "red" if row.rate_limited else ("yellow" if row.status_code >= 400 else "green"),
        }
        for row in rows
    ]
    rate_limited_rows = (
        db.query(FetchRecord)
        .filter(FetchRecord.rate_limited.is_(True))
        .order_by(FetchRecord.fetched_at.desc())
        .limit(40)
        .all()
    )
    domain_rows = (
        db.query(
            FetchRecord.domain,
            func.count(FetchRecord.id),
            func.max(FetchRecord.backoff_applied_s),
            func.max(FetchRecord.fetched_at),
        )
        .filter(FetchRecord.rate_limited.is_(True))
        .group_by(FetchRecord.domain)
        .all()
    )
    backoff_domains = [
        {
            "domain": domain,
            "rate_limited": int(count),
            "max_backoff_s": float(max_backoff or 0),
            "last_at": to_iso(last_at),
        }
        for domain, count, max_backoff, last_at in domain_rows
    ]
    backoff_domains.sort(key=lambda item: (-item["rate_limited"], item["domain"]))
    return {
        "events": events,
        "rate_limited_events": [serialize_fetch(row) for row in rate_limited_rows],
        "backoff_domains": backoff_domains,
        "window": f"最近 {len(events)} 条抓取记录（按抓取时间倒序）",
    }
