"""采集任务与调度模拟服务（算法 B 的落库封装）。"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import FetchOrigin, TaskStatus, UrlStatus
from src.constants.limits import DEFAULT_SIM_MAX_SEQUENCE, DEFAULT_SIM_SEED, DEFAULT_SIM_WINDOW_S
from src.constants.roles import ROLE_ADMIN, ROLE_ENGINEER
from src.models.crawl_task import CrawlTask
from src.models.fetch_record import FetchRecord
from src.models.frontier_url import FrontierUrl
from src.models.seed_site import SeedSite
from src.models.user import User
from src.services import audit_service, scheduler
from src.utils.errors import AppError, not_found
from src.utils.timeutil import to_iso, utcnow


def _parse_json(raw: str | None, fallback):
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except ValueError:
        return fallback


def serialize_task(task: CrawlTask, *, include_result: bool = False) -> dict:
    result = _parse_json(task.scheduler_result, None)
    payload = {
        "id": str(task.id),
        "name": task.name,
        "site_domains": _parse_json(task.site_ids, []),
        "concurrency": task.concurrency,
        "quota_snapshot": _parse_json(task.quota_snapshot, {}),
        "status": task.status,
        "seed": task.seed,
        "window_s": task.window_s,
        "max_sequence": task.max_sequence,
        "scheduled_count": task.scheduled_count,
        "created_by": task.created_by,
        "started_at": to_iso(task.started_at),
        "finished_at": to_iso(task.finished_at),
        "created_at": to_iso(task.created_at),
        "has_result": result is not None,
        "result_summary": (
            {
                "sequence_length": result.get("sequence_length"),
                "rate_limited_count": result.get("rate_limited_count"),
                "starvation_count": len(result.get("starvation_boosts", [])),
                "elapsed_s": result.get("elapsed_s"),
                "digest": result.get("digest"),
            }
            if result
            else None
        ),
    }
    if include_result:
        payload["scheduler_result"] = result
    return payload


def list_tasks(db: Session) -> dict:
    rows = db.query(CrawlTask).order_by(CrawlTask.created_at.asc()).all()
    items = [serialize_task(row) for row in rows]
    summary = {
        "total": len(items),
        "queued": sum(1 for item in items if item["status"] == TaskStatus.QUEUED.value),
        "running": sum(1 for item in items if item["status"] == TaskStatus.RUNNING.value),
        "paused": sum(1 for item in items if item["status"] == TaskStatus.PAUSED.value),
        "finished": sum(1 for item in items if item["status"] == TaskStatus.FINISHED.value),
        "scheduled_total": sum(item["scheduled_count"] for item in items),
    }
    return {"items": items, "summary": summary}


def get_task(db: Session, task_id: str) -> CrawlTask:
    task = db.get(CrawlTask, task_id)
    if task is None:
        raise not_found("CrawlTask", task_id)
    return task


def get_task_detail(db: Session, task_id: str) -> dict:
    return serialize_task(get_task(db, task_id), include_result=True)


def create_task(db: Session, payload: dict, *, actor: User, ip=None, trace_id=None) -> dict:
    if actor.role not in (ROLE_ADMIN, ROLE_ENGINEER):
        raise AppError(codes.FORBIDDEN, "当前角色没有创建任务的权限", f"role={actor.role}")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise AppError(codes.VALIDATION_ERROR, "任务名称不能为空")
    exists = db.query(CrawlTask).filter(CrawlTask.name == name).one_or_none()
    if exists is not None:
        raise AppError(codes.CONFLICT, "任务名称已存在", f"name={name}")
    domains = payload.get("site_domains") or []
    if not isinstance(domains, list) or not domains:
        raise AppError(codes.VALIDATION_ERROR, "至少选择 1 个站点")
    sites = db.query(SeedSite).filter(SeedSite.domain.in_(domains)).all()
    found = {site.domain for site in sites}
    missing = [domain for domain in domains if domain not in found]
    if missing:
        raise AppError(codes.VALIDATION_ERROR, "站点不存在", f"missing={missing}")
    concurrency = int(payload.get("concurrency") or 3)
    if not 1 <= concurrency <= 10:
        raise AppError(codes.VALIDATION_ERROR, "并发需在 1~10 之间")
    window_s = float(payload.get("window_s") or DEFAULT_SIM_WINDOW_S)
    if not 1 <= window_s <= 120:
        raise AppError(codes.VALIDATION_ERROR, "调度窗口需在 1~120 秒之间")
    max_sequence = int(payload.get("max_sequence") or DEFAULT_SIM_MAX_SEQUENCE)
    if not 1 <= max_sequence <= 200:
        raise AppError(codes.VALIDATION_ERROR, "序列上限需在 1~200 之间")
    seed = int(payload.get("seed") or DEFAULT_SIM_SEED)
    quota_snapshot = {
        site.domain: {
            "qps_quota": site.qps_quota,
            "crawl_delay_s": site.crawl_delay_s,
            "max_concurrency": site.max_concurrency,
            "priority": site.priority,
        }
        for site in sorted(sites, key=lambda item: item.domain)
    }
    task = CrawlTask(
        name=name,
        site_ids=json.dumps([site.domain for site in sorted(sites, key=lambda item: item.domain)]),
        concurrency=concurrency,
        quota_snapshot=json.dumps(quota_snapshot, ensure_ascii=False),
        status=TaskStatus.QUEUED.value,
        seed=seed,
        window_s=window_s,
        max_sequence=max_sequence,
        created_by=actor.email,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    audit_service.record(
        db,
        action="task.create",
        entity_type="CrawlTask",
        entity_id=task.id,
        actor=actor,
        payload={"name": task.name, "sites": domains, "window_s": window_s, "max_sequence": max_sequence},
        ip=ip,
        trace_id=trace_id,
    )
    return serialize_task(task, include_result=True)


def _site_configs(db: Session, domains: list[str]) -> list[scheduler.SiteConfig]:
    sites = db.query(SeedSite).filter(SeedSite.domain.in_(domains)).all()
    configs: list[scheduler.SiteConfig] = []
    for site in sorted(sites, key=lambda item: item.domain):
        configs.append(
            scheduler.SiteConfig(
                domain=site.domain,
                name=site.name,
                qps_quota=site.qps_quota,
                crawl_delay_s=site.crawl_delay_s,
                max_concurrency=site.max_concurrency,
                priority=site.priority,
                robots_status=site.robots_status,
                robots_rules=site.robots_rules,
                enabled=site.enabled,
            )
        )
    return configs


def _queued_urls(db: Session, domains: list[str]) -> list[scheduler.UrlItem]:
    sites = {site.domain: site for site in db.query(SeedSite).filter(SeedSite.domain.in_(domains)).all()}
    rows = (
        db.query(FrontierUrl)
        .filter(
            FrontierUrl.site_id.in_([site.id for site in sites.values()]),
            FrontierUrl.is_duplicate.is_(False),
            FrontierUrl.status == UrlStatus.QUEUED.value,
        )
        .order_by(FrontierUrl.raw_url.asc())
        .all()
    )
    items: list[scheduler.UrlItem] = []
    for row in rows:
        site = next((site for site in sites.values() if site.id == row.site_id), None)
        if site is None:
            continue
        items.append(
            scheduler.UrlItem(
                url_id=str(row.id),
                domain=site.domain,
                raw_url=row.raw_url,
                canonical_url=row.canonical_url,
                depth=row.depth,
                priority_score=float(site.priority),
                wait_seconds=float(row.wait_seconds),
            )
        )
    return items


def simulate_task(db: Session, task_id: str, *, actor: User, ip=None, trace_id=None) -> dict:
    if actor.role not in (ROLE_ADMIN, ROLE_ENGINEER):
        raise AppError(codes.FORBIDDEN, "当前角色没有运行调度模拟的权限", f"role={actor.role}")
    task = get_task(db, task_id)
    domains = _parse_json(task.site_ids, [])
    configs = _site_configs(db, domains)
    urls = _queued_urls(db, domains)
    if not urls:
        raise AppError(codes.CONFLICT, "任务站点下没有排队中的前沿 URL", f"task={task.name}")
    now = utcnow()
    result = scheduler.simulate(
        configs,
        urls,
        task_name=task.name,
        window_s=task.window_s,
        max_sequence=task.max_sequence,
        seed=task.seed,
        now=now,
    )
    task.status = TaskStatus.FINISHED.value
    task.scheduled_count = int(result["sequence_length"])
    task.scheduler_result = json.dumps(result, ensure_ascii=False)
    task.started_at = now
    task.finished_at = now
    task.quota_snapshot = json.dumps(
        {
            config.domain: {
                "qps_quota": config.qps_quota,
                "crawl_delay_s": config.crawl_delay_s,
                "max_concurrency": config.max_concurrency,
                "priority": config.priority,
            }
            for config in configs
        },
        ensure_ascii=False,
    )
    db.add(task)
    # 调度模拟生成的抓取记录：先清掉本任务上次模拟记录（可重复运行且不重复堆积）
    db.query(FetchRecord).filter(
        FetchRecord.task_id == task.id, FetchRecord.origin == FetchOrigin.SIMULATION.value
    ).delete(synchronize_session=False)
    for item in result["sequence"]:
        db.add(
            FetchRecord(
                task_id=task.id,
                url_id=item["url_id"],
                domain=item["domain"],
                status_code=item["status_code"],
                latency_ms=item["latency_ms"],
                bytes=1024 + (item["seq"] * 37) % 4096,
                was_duplicate=False,
                rate_limited=item["rate_limited"],
                backoff_applied_s=item["backoff_applied_s"],
                origin=FetchOrigin.SIMULATION.value,
                fetched_at=now,
            )
        )
    db.commit()
    db.refresh(task)
    audit_service.record(
        db,
        action="task.simulate",
        entity_type="CrawlTask",
        entity_id=task.id,
        actor=actor,
        payload={
            "sequence_length": result["sequence_length"],
            "rate_limited": result["rate_limited_count"],
            "starvation": len(result["starvation_boosts"]),
            "digest": result["digest"],
        },
        ip=ip,
        trace_id=trace_id,
    )
    return serialize_task(task, include_result=True)
