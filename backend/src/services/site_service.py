"""站点（域）清单与礼貌配额配置服务。"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import RobotsStatus
from src.constants.roles import ROLE_ADMIN
from src.models.seed_site import SeedSite
from src.models.user import User
from src.services import audit_service
from src.utils.errors import AppError, not_found
from src.utils.robots import parse_rules
from src.utils.timeutil import to_iso

EDITABLE_FIELDS = (
    "qps_quota",
    "crawl_delay_s",
    "max_concurrency",
    "priority",
    "enabled",
    "robots_status",
    "robots_rules",
)


def serialize_site(site: SeedSite) -> dict:
    rules = parse_rules(site.robots_rules)
    return {
        "id": str(site.id),
        "domain": site.domain,
        "name": site.name,
        "robots_status": site.robots_status,
        "robots_disallow": rules["disallow"],
        "robots_allow": rules["allow"],
        "crawl_delay_s": site.crawl_delay_s,
        "qps_quota": site.qps_quota,
        "max_concurrency": site.max_concurrency,
        "priority": site.priority,
        "sitemap_declared": site.sitemap_declared,
        "enabled": site.enabled,
        "last_audited_at": to_iso(site.last_audited_at),
    }


def list_sites(db: Session) -> dict:
    sites = db.query(SeedSite).order_by(SeedSite.priority.desc(), SeedSite.domain.asc()).all()
    items = [serialize_site(site) for site in sites]
    summary = {
        "total": len(items),
        "allow": sum(1 for item in items if item["robots_status"] == RobotsStatus.ALLOW.value),
        "partial": sum(1 for item in items if item["robots_status"] == RobotsStatus.PARTIAL.value),
        "blocked": sum(1 for item in items if item["robots_status"] == RobotsStatus.BLOCKED.value),
        "enabled": sum(1 for item in items if item["enabled"]),
        "total_qps": round(sum(item["qps_quota"] for item in items if item["enabled"]), 2),
    }
    return {"items": items, "summary": summary}


def get_site(db: Session, site_id: str) -> SeedSite:
    site = db.get(SeedSite, site_id)
    if site is None:
        raise not_found("SeedSite", site_id)
    return site


def update_site(
    db: Session,
    site_id: str,
    payload: dict,
    *,
    actor: User,
    ip: str | None = None,
    trace_id: str | None = None,
) -> dict:
    if actor.role != ROLE_ADMIN:
        raise AppError(codes.FORBIDDEN, "只有调度主管可以修改站点配额", f"role={actor.role}")
    site = get_site(db, site_id)
    changes: dict[str, object] = {}
    for field in EDITABLE_FIELDS:
        if field not in payload or payload[field] is None:
            continue
        value = payload[field]
        if field == "qps_quota":
            value = float(value)
            if not 0.1 <= value <= 20:
                raise AppError(codes.VALIDATION_ERROR, "qps_quota 需在 0.1~20 之间", f"got={value}")
        elif field == "crawl_delay_s":
            value = float(value)
            if not 0 <= value <= 60:
                raise AppError(codes.VALIDATION_ERROR, "crawl_delay_s 需在 0~60 秒之间", f"got={value}")
        elif field == "max_concurrency":
            value = int(value)
            if not 1 <= value <= 16:
                raise AppError(codes.VALIDATION_ERROR, "max_concurrency 需在 1~16 之间", f"got={value}")
        elif field == "priority":
            value = int(value)
            if not 1 <= value <= 5:
                raise AppError(codes.VALIDATION_ERROR, "priority 需在 1~5 之间", f"got={value}")
        elif field == "enabled":
            value = bool(value)
        elif field == "robots_status":
            value = str(value).lower()
            if value not in {item.value for item in RobotsStatus}:
                raise AppError(codes.VALIDATION_ERROR, "robots_status 非法", f"got={value}")
        elif field == "robots_rules":
            value = json.dumps(value if isinstance(value, dict) else json.loads(str(value)), ensure_ascii=False)
        old = getattr(site, field)
        if old != value:
            changes[field] = {"from": old, "to": value}
            setattr(site, field, value)
    if not changes:
        return {"site": serialize_site(site), "changes": {}, "changed": False}
    db.add(site)
    db.commit()
    db.refresh(site)
    audit_service.record(
        db,
        action="site.update",
        entity_type="SeedSite",
        entity_id=site.id,
        actor=actor,
        payload={"domain": site.domain, "changes": changes},
        ip=ip,
        trace_id=trace_id,
    )
    return {"site": serialize_site(site), "changes": changes, "changed": True}
