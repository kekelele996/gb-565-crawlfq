"""URL 前沿服务：规范化预览、布隆过滤器去重统计、域分组列表。"""
from __future__ import annotations

import json
import threading

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import UrlStatus
from src.models.frontier_url import FrontierUrl
from src.models.seed_site import SeedSite
from src.services import canonicalizer
from src.utils.bloom_filter import BloomFilter
from src.utils.errors import AppError
from src.utils.pagination import normalize_pagination
from src.utils.timeutil import to_iso

_bloom_lock = threading.Lock()
_bloom: BloomFilter | None = None
_bloom_target: tuple[int, int] | None = None


def reset_index() -> None:
    global _bloom, _bloom_target
    with _bloom_lock:
        _bloom = None
        _bloom_target = None


def get_index(db: Session) -> BloomFilter:
    """进程内布隆过滤器（seed 后由 lifespan 调用 reset_index 触发重建）。

    按 canonical_url 字典序插入，保证多次构建位图/统计完全一致。
    """
    global _bloom, _bloom_target
    with _bloom_lock:
        if _bloom is not None:
            return _bloom
        bits = int(settings.bloom_bits)
        k = int(settings.bloom_k)
        bloom = BloomFilter(bits=bits, k=k)
        rows = (
            db.query(FrontierUrl.canonical_url)
            .filter(FrontierUrl.is_duplicate.is_(False))
            .order_by(FrontierUrl.canonical_url.asc())
            .all()
        )
        for (canonical_url,) in rows:
            bloom.add(canonical_url)
        _bloom = bloom
        _bloom_target = (bits, k)
        return bloom


def _parse_reasons(raw: str) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except ValueError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def stats(db: Session) -> dict:
    bloom = get_index(db)
    total = db.query(func.count(FrontierUrl.id)).scalar() or 0
    unique = (
        db.query(func.count(FrontierUrl.id)).filter(FrontierUrl.is_duplicate.is_(False)).scalar() or 0
    )
    duplicated = (
        db.query(func.count(FrontierUrl.id)).filter(FrontierUrl.is_duplicate.is_(True)).scalar() or 0
    )
    status_rows = (
        db.query(FrontierUrl.status, func.count(FrontierUrl.id))
        .group_by(FrontierUrl.status)
        .all()
    )
    status_counts = {status: int(count) for status, count in status_rows}
    domain_rows = (
        db.query(SeedSite.domain, SeedSite.name)
        .join(FrontierUrl, FrontierUrl.site_id == SeedSite.id)
        .group_by(SeedSite.domain, SeedSite.name)
        .all()
    )
    by_domain: list[dict] = []
    for domain, name in domain_rows:
        rows = (
            db.query(FrontierUrl)
            .join(SeedSite, SeedSite.id == FrontierUrl.site_id)
            .filter(SeedSite.domain == domain)
            .all()
        )
        by_domain.append(
            {
                "domain": domain,
                "name": name,
                "raw": len(rows),
                "unique": sum(1 for row in rows if not row.is_duplicate),
                "folded": sum(1 for row in rows if row.is_duplicate),
                "queued": sum(1 for row in rows if row.status == UrlStatus.QUEUED.value),
                "done": sum(1 for row in rows if row.status == UrlStatus.DONE.value),
                "blocked": sum(1 for row in rows if row.status == UrlStatus.BLOCKED.value),
            }
        )
    by_domain.sort(key=lambda item: (-item["raw"], item["domain"]))
    reason_histogram: dict[str, int] = {}
    for (raw_reasons,) in db.query(FrontierUrl.change_reasons).filter(
        FrontierUrl.is_duplicate.is_(False)
    ):
        for reason in _parse_reasons(raw_reasons):
            reason_histogram[reason] = reason_histogram.get(reason, 0) + 1
    return {
        "raw": int(total),
        "unique": int(unique),
        "folded": int(duplicated),
        "status_counts": status_counts,
        "by_domain": by_domain,
        "reason_histogram": dict(
            sorted(reason_histogram.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        "bloom": bloom.stats(),
        "formula": "canonical = 规则归一；fingerprint = sha256(canonical)；布隆过滤器 m=2^20, k=5, "
        "误判率估计 (1-e^(-kn/m))^k",
    }


def _site_map(db: Session) -> dict[str, SeedSite]:
    return {site.id: site for site in db.query(SeedSite).all()}


def serialize_url(row: FrontierUrl, site: SeedSite | None) -> dict:
    return {
        "id": str(row.id),
        "domain": site.domain if site else "",
        "site_name": site.name if site else "",
        "raw_url": row.raw_url,
        "canonical_url": row.canonical_url,
        "fingerprint": row.fingerprint,
        "fingerprint_short": row.fingerprint[:12],
        "source": row.source,
        "depth": row.depth,
        "priority_score": row.priority_score,
        "status": row.status,
        "wait_seconds": row.wait_seconds,
        "is_duplicate": row.is_duplicate,
        "folded_into_id": str(row.folded_into_id) if row.folded_into_id else None,
        "change_reasons": _parse_reasons(row.change_reasons),
        "discovered_at": to_iso(row.discovered_at),
    }


def list_urls(
    db: Session,
    *,
    domain: str | None = None,
    status: str | None = None,
    duplicate: str | None = None,
    q: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> dict:
    page, page_size = normalize_pagination(page, page_size)
    query = db.query(FrontierUrl).join(SeedSite, SeedSite.id == FrontierUrl.site_id)
    if domain:
        query = query.filter(SeedSite.domain == domain)
    if status:
        query = query.filter(FrontierUrl.status == status)
    if duplicate == "only":
        query = query.filter(FrontierUrl.is_duplicate.is_(True))
    elif duplicate == "exclude":
        query = query.filter(FrontierUrl.is_duplicate.is_(False))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(FrontierUrl.raw_url.ilike(like))
    total = query.count()
    rows = (
        query.order_by(FrontierUrl.is_duplicate.asc(), FrontierUrl.discovered_at.asc(), FrontierUrl.raw_url.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    sites = _site_map(db)
    return {
        "items": [serialize_url(row, sites.get(row.site_id)) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def preview(db: Session, raw_url: str) -> dict:
    try:
        result = canonicalizer.canonicalize(raw_url)
    except canonicalizer.CanonicalError as exc:
        raise AppError(codes.VALIDATION_ERROR, "URL 无法规范化", str(exc)) from exc
    bloom = get_index(db)
    existing = (
        db.query(FrontierUrl)
        .filter(FrontierUrl.fingerprint == result["fingerprint"])
        .order_by(FrontierUrl.is_duplicate.asc(), FrontierUrl.raw_url.asc())
        .first()
    )
    return {
        **result,
        "bloom_hit": bool(existing) or bloom.might_contain(result["canonical_url"]),
        "existing": serialize_url(existing, db.get(SeedSite, existing.site_id)) if existing else None,
        "is_duplicate": bool(existing),
    }


def examples(db: Session, limit: int = 3) -> list[dict]:
    """挑 3 条真实 seed 行做规范化前后对比：query 排序 / utm 剔除 / index.html 归一。"""
    wanted = ["query_sorted", "tracking_param_removed", "index_page_to_root", "fragment_removed"]
    rows = (
        db.query(FrontierUrl)
        .filter(FrontierUrl.is_duplicate.is_(False))
        .order_by(FrontierUrl.raw_url.asc())
        .all()
    )
    sites = _site_map(db)
    picked: list[dict] = []
    used: set[str] = set()
    for keyword in wanted:
        for row in rows:
            reasons = _parse_reasons(row.change_reasons)
            joined = " ".join(reasons)
            if keyword in joined and row.raw_url not in used:
                payload = serialize_url(row, sites.get(row.site_id))
                payload["example_kind"] = keyword
                picked.append(payload)
                used.add(row.raw_url)
                break
        if len(picked) >= limit:
            break
    if not picked:
        picked = [serialize_url(row, sites.get(row.site_id)) for row in rows[:limit]]
    return picked[:limit]


def fold_summary_for_seed(rows: list[dict]) -> dict:
    """seed 用：对 [{site_id, raw_url}] 跑算法 A 折叠（复用 fold_urls）。"""
    return canonicalizer.fold_urls(rows)
