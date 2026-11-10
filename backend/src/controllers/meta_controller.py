"""元信息 controller：健康检查 / 总览 / 审计日志。"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config.database import ping_db
from src.models.coverage_audit import CoverageAudit
from src.models.crawl_task import CrawlTask
from src.models.fetch_record import FetchRecord
from src.models.frontier_url import FrontierUrl
from src.models.seed_site import SeedSite
from src.services import audit_service, frontier_service
from src.utils.redis_client import ping_redis

SERVICE = "crawlfq-backend"
VERSION = "1.0.0"


def health(db: Session) -> dict:
    db_ok = ping_db()
    redis_ok = ping_redis()
    return {
        "status": "ok" if db_ok and redis_ok else "degraded",
        "service": SERVICE,
        "version": VERSION,
        "db": "up" if db_ok else "down",
        "redis": "up" if redis_ok else "down",
    }


def overview(db: Session) -> dict:
    stats = frontier_service.stats(db)
    return {
        "sites": db.query(func.count(SeedSite.id)).scalar() or 0,
        "frontier": {
            "raw": stats["raw"],
            "unique": stats["unique"],
            "folded": stats["folded"],
            "queued": stats["status_counts"].get("queued", 0),
            "done": stats["status_counts"].get("done", 0),
        },
        "bloom": {
            "false_positive_pct": stats["bloom"]["false_positive_pct"],
            "inserted": stats["bloom"]["inserted"],
        },
        "tasks": db.query(func.count(CrawlTask.id)).scalar() or 0,
        "fetches": db.query(func.count(FetchRecord.id)).scalar() or 0,
        "rate_limited": db.query(func.count(FetchRecord.id))
        .filter(FetchRecord.rate_limited.is_(True))
        .scalar()
        or 0,
        "audits": db.query(func.count(CoverageAudit.id)).scalar() or 0,
    }


def audit_logs(db: Session, limit: int = 50) -> dict:
    return {"items": audit_service.list_logs(db, limit=limit)}
