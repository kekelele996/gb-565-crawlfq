"""覆盖度审计服务：sitemap 声明 / 已发现 / 已抓 / 覆盖率 / 缺口 CSV。

口径：coverage_ratio = fetched / sitemap_declared（保留 4 位小数）
缺口：gap_count = max(0, declared - fetched)；每条缺口带 url + reason，
      优先取真实 URL（robots 禁止 / 失败 / 排队中），不足时补 sitemap 声明清单
      中的占位条目（not_discovered，等价于“声明了但没发现 URL”）。
"""
from __future__ import annotations

import csv
import io
import json

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import GAP_REASON_LABELS, GapReason, UrlStatus
from src.models.coverage_audit import CoverageAudit
from src.models.frontier_url import FrontierUrl
from src.models.seed_site import SeedSite
from src.models.user import User
from src.services import audit_service
from src.utils.errors import AppError, not_found
from src.utils.timeutil import to_iso, utcnow

STATUS_TO_REASON = {
    UrlStatus.BLOCKED.value: GapReason.ROBOTS_BLOCKED.value,
    UrlStatus.FAILED.value: GapReason.FETCH_FAILED.value,
    UrlStatus.QUEUED.value: GapReason.OVER_QUOTA.value,
    UrlStatus.INFLIGHT.value: GapReason.OVER_QUOTA.value,
}
STATUS_RANK = {
    UrlStatus.BLOCKED.value: 0,
    UrlStatus.FAILED.value: 1,
    UrlStatus.QUEUED.value: 2,
    UrlStatus.INFLIGHT.value: 3,
}
CSV_HEADER = [
    "audit_batch",
    "site_domain",
    "url",
    "reason",
    "reason_label",
    "depth",
    "declared",
    "fetched",
    "coverage_ratio",
]


def _parse_gaps(raw: str) -> list[dict]:
    try:
        value = json.loads(raw or "[]")
    except ValueError:
        return []
    return value if isinstance(value, list) else []


def serialize_audit(row: CoverageAudit, *, include_gaps: bool = False) -> dict:
    payload = {
        "id": str(row.id),
        "site_domain": row.site_domain,
        "batch_label": row.batch_label,
        "sitemap_declared": row.sitemap_declared,
        "discovered": row.discovered,
        "fetched": row.fetched,
        "coverage_ratio": row.coverage_ratio,
        "coverage_pct": round(row.coverage_ratio * 100, 2),
        "gap_count": row.gap_count,
        "created_at": to_iso(row.created_at),
    }
    if include_gaps:
        payload["gaps"] = _parse_gaps(row.gaps)
    return payload


def list_audits(db: Session) -> dict:
    rows = db.query(CoverageAudit).order_by(CoverageAudit.created_at.asc(), CoverageAudit.site_domain.asc()).all()
    items = [
        {**serialize_audit(row, include_gaps=True), "gaps": _parse_gaps(row.gaps)[:40]}
        for row in rows
    ]
    summary = {
        "total": len(items),
        "declared_total": sum(item["sitemap_declared"] for item in items),
        "fetched_total": sum(item["fetched"] for item in items),
        "gap_total": sum(item["gap_count"] for item in items),
        "avg_coverage": round(
            sum(item["coverage_ratio"] for item in items) / len(items), 4
        )
        if items
        else 0.0,
    }
    return {"items": items, "summary": summary}


def get_audit(db: Session, audit_id: str, *, include_gaps: bool = True) -> dict:
    row = db.get(CoverageAudit, audit_id)
    if row is None:
        raise not_found("CoverageAudit", audit_id)
    return serialize_audit(row, include_gaps=include_gaps)


def _build_gaps(
    urls: list[FrontierUrl], *, site: SeedSite, declared: int, fetched: int
) -> list[dict]:
    gap_count = max(0, declared - fetched)
    ordered = sorted(
        [url for url in urls if url.status != UrlStatus.DONE.value],
        key=lambda url: (STATUS_RANK.get(url.status, 9), url.raw_url),
    )
    gaps: list[dict] = []
    for url in ordered[:gap_count]:
        reason = STATUS_TO_REASON.get(url.status, GapReason.NOT_DISCOVERED.value)
        gaps.append(
            {
                "url": url.canonical_url,
                "raw_url": url.raw_url,
                "reason": reason,
                "depth": url.depth,
            }
        )
    index = 0
    while len(gaps) < gap_count:
        gaps.append(
            {
                "url": f"https://{site.domain}/sitemap-entry/{index:03d}",
                "raw_url": f"https://{site.domain}/sitemap-entry/{index:03d}",
                "reason": GapReason.NOT_DISCOVERED.value,
                "depth": 0,
            }
        )
        index += 1
    return gaps


def run_audit(
    db: Session,
    *,
    site_domain: str,
    batch_label: str,
    actor: User | None = None,
    skip_if_exists: bool = False,
    now=None,
    ip: str | None = None,
    trace_id: str | None = None,
) -> dict:
    site = db.query(SeedSite).filter(SeedSite.domain == site_domain).one_or_none()
    if site is None:
        raise AppError(codes.NOT_FOUND, "站点不存在", f"domain={site_domain}")
    existing = (
        db.query(CoverageAudit)
        .filter(CoverageAudit.site_domain == site_domain, CoverageAudit.batch_label == batch_label)
        .one_or_none()
    )
    if existing is not None and skip_if_exists:
        return serialize_audit(existing, include_gaps=True)
    urls = (
        db.query(FrontierUrl)
        .filter(FrontierUrl.site_id == site.id, FrontierUrl.is_duplicate.is_(False))
        .order_by(FrontierUrl.raw_url.asc())
        .all()
    )
    declared = int(site.sitemap_declared or len(urls))
    discovered = min(declared, len(urls)) if declared else len(urls)
    fetched = sum(1 for url in urls if url.status == UrlStatus.DONE.value)
    ratio = round(fetched / declared, 4) if declared else 0.0
    gaps = _build_gaps(urls, site=site, declared=declared, fetched=fetched)
    created_at = now or utcnow()
    if existing is None:
        row = CoverageAudit(
            site_id=site.id,
            site_domain=site.domain,
            batch_label=batch_label,
            sitemap_declared=declared,
            discovered=discovered,
            fetched=fetched,
            coverage_ratio=ratio,
            gap_count=len(gaps),
            gaps=json.dumps(gaps, ensure_ascii=False),
            created_at=created_at,
        )
        db.add(row)
    else:
        row = existing
        row.sitemap_declared = declared
        row.discovered = discovered
        row.fetched = fetched
        row.coverage_ratio = ratio
        row.gap_count = len(gaps)
        row.gaps = json.dumps(gaps, ensure_ascii=False)
        db.add(row)
    site.last_audited_at = created_at
    db.add(site)
    db.commit()
    db.refresh(row)
    if actor is not None:
        audit_service.record(
            db,
            action="coverage.run",
            entity_type="CoverageAudit",
            entity_id=row.id,
            actor=actor,
            payload={
                "site": site.domain,
                "declared": declared,
                "fetched": fetched,
                "ratio": ratio,
                "gaps": len(gaps),
            },
            ip=ip,
            trace_id=trace_id,
        )
    return serialize_audit(row, include_gaps=True)


def gaps_csv(db: Session, *, audit_ids: list[str] | None = None) -> tuple[str, int]:
    query = db.query(CoverageAudit).order_by(CoverageAudit.created_at.asc(), CoverageAudit.site_domain.asc())
    if audit_ids:
        query = query.filter(CoverageAudit.id.in_(audit_ids))
    rows = query.all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADER)
    data_rows = 0
    for audit in rows:
        for gap in _parse_gaps(audit.gaps):
            writer.writerow(
                [
                    audit.batch_label,
                    audit.site_domain,
                    gap.get("url", ""),
                    gap.get("reason", ""),
                    GAP_REASON_LABELS.get(gap.get("reason", ""), gap.get("reason", "")),
                    gap.get("depth", 0),
                    audit.sitemap_declared,
                    audit.fetched,
                    audit.coverage_ratio,
                ]
            )
            data_rows += 1
    return buffer.getvalue(), data_rows
