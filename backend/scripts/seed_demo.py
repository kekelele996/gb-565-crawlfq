"""crawlfq 演示数据 seed（幂等；SEED_DEMO=true 时由启动 lifespan 自动执行一次）。

生成内容与批次日工作剧本一致：
- 6 个站点（1 个 robots partial）、300 raw URL（含 40 个重复变体 → 260 唯一）
- 3 个采集任务（2 个已跑过真实调度模拟，1 个留给主流程）
- 500 条抓取记录（含 12 次 429 加退避）
- 2 条覆盖度审计：今日头条 88/120=73.33%，澎湃 110/125=88.00%
- 3 个账号（admin/engineer/viewer，密码 Demo@2026）
结束时打印一行固定顺序的 SEED_SUMMARY，两次执行必须逐字一致。
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.config.database import SessionLocal
from src.constants.enums import FetchOrigin, TaskStatus, UrlStatus
from src.models.coverage_audit import CoverageAudit
from src.models.crawl_task import CrawlTask
from src.models.fetch_record import FetchRecord
from src.models.frontier_url import FrontierUrl
from src.models.seed_site import SeedSite
from src.models.user import User
from src.services import canonicalizer, coverage_service, scheduler
from src.services.task_service import _queued_urls, _site_configs
from src.utils.logger import get_logger
from src.utils.password import hash_password

logger = get_logger("crawlfq.seed")

DEMO_PASSWORD = "Demo@2026"
BRAND = "crawlfq"
BASE_UTC = datetime(2026, 11, 9, 22, 0, tzinfo=timezone.utc)  # 2026-11-10 06:00 +08:00
AUDIT_BASE_UTC = datetime(2026, 11, 9, 22, 0, tzinfo=timezone.utc)

USERS = [
    {
        "email": "admin@crawlfq.io",
        "display_name": "陈可欣",
        "role": "admin",
    },
    {
        "email": "engineer@crawlfq.io",
        "display_name": "林舟",
        "role": "engineer",
    },
    {
        "email": "viewer@crawlfq.io",
        "display_name": "周敏",
        "role": "viewer",
    },
]

SITES = [
    {
        "domain": "www.toutiao.com",
        "name": "今日头条",
        "robots_status": "allow",
        "robots_rules": {"disallow": [], "allow": []},
        "crawl_delay_s": 0.5,
        "qps_quota": 3.0,
        "max_concurrency": 3,
        "priority": 5,
        "sitemap_declared": 120,
    },
    {
        "domain": "www.thepaper.cn",
        "name": "澎湃新闻",
        "robots_status": "allow",
        "robots_rules": {"disallow": [], "allow": []},
        "crawl_delay_s": 1.0,
        "qps_quota": 2.0,
        "max_concurrency": 2,
        "priority": 4,
        "sitemap_declared": 125,
    },
    {
        "domain": "www.36kr.com",
        "name": "36氪",
        "robots_status": "allow",
        "robots_rules": {"disallow": [], "allow": []},
        "crawl_delay_s": 1.0,
        "qps_quota": 2.0,
        "max_concurrency": 2,
        "priority": 3,
        "sitemap_declared": 90,
    },
    {
        "domain": "www.jiemian.com",
        "name": "界面新闻",
        "robots_status": "allow",
        "robots_rules": {"disallow": [], "allow": []},
        "crawl_delay_s": 1.5,
        "qps_quota": 1.0,
        "max_concurrency": 2,
        "priority": 3,
        "sitemap_declared": 60,
    },
    {
        "domain": "finance.sina.com.cn",
        "name": "新浪财经",
        "robots_status": "partial",
        "robots_rules": {"disallow": ["/cj/", "/roll/"], "allow": ["/cj/2026/"]},
        "crawl_delay_s": 2.0,
        "qps_quota": 1.0,
        "max_concurrency": 1,
        "priority": 2,
        "sitemap_declared": 70,
    },
    {
        "domain": "www.caixin.com",
        "name": "财新网",
        "robots_status": "allow",
        "robots_rules": {"disallow": [], "allow": []},
        "crawl_delay_s": 2.0,
        "qps_quota": 1.0,
        "max_concurrency": 1,
        "priority": 2,
        "sitemap_declared": 50,
    },
]


def _stable_int(*parts: object) -> int:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _base_urls(site: dict) -> list[dict]:
    """按站点配额生成唯一 URL 清单（数量与覆盖度审计口径对齐）。"""
    domain = site["domain"]
    specs: list[dict] = []
    if domain == "www.toutiao.com":
        total, done = 128, 88
        for index in range(total):
            path = f"/article/{7300000000000000000 + index}/"
            query = ""
            if index % 7 == 0:
                query = f"?source=news&seq={index}"
            if index % 11 == 0:
                query += ("&" if query else "?") + "utm_campaign=daily"
            if index == 127:
                query = "?source=feed#comments"
            raw = f"https://www.toutiao.com{path}{query}"
            status = UrlStatus.DONE.value if index < done else UrlStatus.QUEUED.value
            wait = 0.0 if index < done else float(20 + (index % 6) * 15)
            specs.append(
                {
                    "domain": domain,
                    "raw_url": raw,
                    "status": status,
                    "wait_seconds": wait,
                    "depth": 2,
                    "source": "sitemap" if index % 13 else "link",
                }
            )
    elif domain == "www.thepaper.cn":
        total, done = 113, 110
        for index in range(total):
            if index == 112:
                raw = "https://www.thepaper.cn/index.html"
            else:
                raw = f"https://www.thepaper.cn/newsDetail_forward_{9000000 + index}"
            status = UrlStatus.DONE.value if index < done else UrlStatus.QUEUED.value
            wait = 0.0 if index < done else 240.0
            specs.append(
                {
                    "domain": domain,
                    "raw_url": raw,
                    "status": status,
                    "wait_seconds": wait,
                    "depth": 1,
                    "source": "sitemap" if index % 17 else "link",
                }
            )
    elif domain == "www.36kr.com":
        for index in range(6):
            specs.append(
                {
                    "domain": domain,
                    "raw_url": f"https://www.36kr.com/p/{2700000000000 + index}",
                    "status": UrlStatus.QUEUED.value,
                    "wait_seconds": 60.0,
                    "depth": 2,
                    "source": "sitemap",
                }
            )
    elif domain == "www.jiemian.com":
        for index in range(5):
            specs.append(
                {
                    "domain": domain,
                    "raw_url": f"https://www.jiemian.com/article/{8800000 + index}.html",
                    "status": UrlStatus.QUEUED.value if index == 0 else UrlStatus.BLOCKED.value,
                    "wait_seconds": 420.0 if index == 0 else 0.0,
                    "depth": 2,
                    "source": "seed" if index == 0 else "sitemap",
                }
            )
    elif domain == "finance.sina.com.cn":
        specs.append(
            {
                "domain": domain,
                "raw_url": "https://finance.sina.com.cn/stock/2026-11-10/doc-imzq2026111001.shtml",
                "status": UrlStatus.QUEUED.value,
                "wait_seconds": 520.0,
                "depth": 3,
                "source": "sitemap",
            }
        )
        for index in range(3):
            specs.append(
                {
                    "domain": domain,
                    "raw_url": f"https://finance.sina.com.cn/cj/roll/2026-11-10/doc-cj{index + 1}.shtml",
                    "status": UrlStatus.BLOCKED.value,
                    "wait_seconds": 0.0,
                    "depth": 3,
                    "source": "sitemap",
                }
            )
    elif domain == "www.caixin.com":
        specs.append(
            {
                "domain": domain,
                "raw_url": "https://www.caixin.com/2026-11-10/102261001.html",
                "status": UrlStatus.QUEUED.value,
                "wait_seconds": 780.0,
                "depth": 2,
                "source": "sitemap",
            }
        )
        for index in range(3):
            specs.append(
                {
                    "domain": domain,
                    "raw_url": f"https://www.caixin.com/2026-11-10/102261{index + 2:03d}.html",
                    "status": UrlStatus.BLOCKED.value,
                    "wait_seconds": 0.0,
                    "depth": 2,
                    "source": "sitemap",
                }
            )
    return specs


def _duplicate_variants(base: dict, variant_type: int) -> str:
    """40 个重复变体：utm 剔除 / fragment / 大写 host+默认端口 / 重复斜杠 / 尾斜杠 / sessionid。"""
    raw = base["raw_url"]
    domain = base["domain"]
    if variant_type == 0:
        joiner = "&" if "?" in raw else "?"
        return f"{raw}{joiner}utm_source=wechat&utm_medium=social"
    if variant_type == 1:
        return f"{raw}#comments"
    if variant_type == 2:
        return raw.replace(f"https://{domain}", f"https://{domain.upper()}:443", 1)
    if variant_type == 3:
        return raw.replace(f"https://{domain}", f"https://{domain}//", 1)
    if variant_type == 4:
        head, sep, tail = raw.partition("?")
        return f"{head}/{sep}{tail}"
    joiner = "&" if "?" in raw else "?"
    return f"{raw}{joiner}sessionid=abc{_stable_int(raw) % 900 + 100}"


def _seed_users(db: Session) -> int:
    created = 0
    for spec in USERS:
        existing = db.query(User).filter(User.email == spec["email"]).one_or_none()
        if existing is not None:
            continue
        db.add(
            User(
                email=spec["email"],
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=spec["display_name"],
                role=spec["role"],
                is_active=True,
            )
        )
        created += 1
    db.commit()
    return created


def _seed_sites(db: Session) -> dict[str, SeedSite]:
    for spec in SITES:
        existing = db.query(SeedSite).filter(SeedSite.domain == spec["domain"]).one_or_none()
        if existing is not None:
            continue
        db.add(
            SeedSite(
                domain=spec["domain"],
                name=spec["name"],
                robots_status=spec["robots_status"],
                robots_rules=json.dumps(spec["robots_rules"], ensure_ascii=False),
                crawl_delay_s=spec["crawl_delay_s"],
                qps_quota=spec["qps_quota"],
                max_concurrency=spec["max_concurrency"],
                priority=spec["priority"],
                sitemap_declared=spec["sitemap_declared"],
                enabled=True,
            )
        )
    db.commit()
    return {site.domain: site for site in db.query(SeedSite).all()}


def _seed_frontier(db: Session, sites: dict[str, SeedSite]) -> dict:
    existing = db.query(FrontierUrl).count()
    if existing:
        return {"inserted": 0, "skipped": existing}
    base_specs: list[dict] = []
    for spec in SITES:
        base_specs.extend(_base_urls(spec))
    duplicate_base_indices = [index * 3 for index in range(40)]
    all_specs = list(base_specs)
    for variant_index, base_index in enumerate(duplicate_base_indices):
        base = base_specs[base_index]
        all_specs.append(
            {
                "domain": base["domain"],
                "raw_url": _duplicate_variants(base, variant_index % 6),
                "status": UrlStatus.FOLDED.value,
                "wait_seconds": 0.0,
                "depth": base["depth"],
                "source": base["source"],
            }
        )
    folded = canonicalizer.fold_urls([{"raw_url": spec["raw_url"]} for spec in all_specs])
    stats = folded["stats"]
    if stats["raw"] != 300 or stats["unique"] != 260 or stats["folded"] != 40:
        raise RuntimeError(f"frontier fold invariant broken: {stats}")

    inserted_rows: dict[int, FrontierUrl] = {}
    for item, spec in zip(folded["items"], all_specs):
        if item["is_duplicate"]:
            continue
        row = FrontierUrl(
            site_id=sites[spec["domain"]].id,
            raw_url=item["raw_url"],
            canonical_url=item["canonical_url"],
            fingerprint=item["fingerprint"],
            source=spec["source"],
            depth=spec["depth"],
            priority_score=float(sites[spec["domain"]].priority),
            status=spec["status"],
            wait_seconds=spec["wait_seconds"],
            is_duplicate=False,
            change_reasons=json.dumps(item["change_reasons"], ensure_ascii=False),
            discovered_at=BASE_UTC + timedelta(minutes=item["index"] * 2),
        )
        db.add(row)
        inserted_rows[item["index"]] = row
    db.flush()
    for item, spec in zip(folded["items"], all_specs):
        if not item["is_duplicate"]:
            continue
        primary = inserted_rows.get(int(item["folded_index"]))
        db.add(
            FrontierUrl(
                site_id=sites[spec["domain"]].id,
                raw_url=item["raw_url"],
                canonical_url=item["canonical_url"],
                fingerprint=item["fingerprint"],
                source=spec["source"],
                depth=spec["depth"],
                priority_score=float(sites[spec["domain"]].priority),
                status=UrlStatus.FOLDED.value,
                wait_seconds=0.0,
                is_duplicate=True,
                folded_into_id=primary.id if primary else None,
                change_reasons=json.dumps(item["change_reasons"], ensure_ascii=False),
                discovered_at=BASE_UTC + timedelta(minutes=item["index"] * 2),
            )
        )
    db.commit()
    return {"inserted": stats["raw"], "unique": stats["unique"], "folded": stats["folded"]}


def _seed_tasks(db: Session) -> list[CrawlTask]:
    all_domains = [spec["domain"] for spec in SITES]
    specs = [
        {
            "name": "今日头条要闻增量采集",
            "site_ids": all_domains,
            "concurrency": 3,
            "window_s": 20.0,
            "max_sequence": 40,
            "seed": 7,
            "status": TaskStatus.QUEUED.value,
            "simulate": False,
            "created_by": "admin@crawlfq.io",
        },
        {
            "name": "澎湃深读栏目回填",
            "site_ids": ["www.thepaper.cn"],
            "concurrency": 2,
            "window_s": 20.0,
            "max_sequence": 40,
            "seed": 7,
            "status": TaskStatus.FINISHED.value,
            "simulate": True,
            "created_by": "engineer@crawlfq.io",
        },
        {
            "name": "36氪快讯增量采集",
            "site_ids": ["www.36kr.com"],
            "concurrency": 2,
            "window_s": 20.0,
            "max_sequence": 40,
            "seed": 7,
            "status": TaskStatus.FINISHED.value,
            "simulate": True,
            "created_by": "engineer@crawlfq.io",
        },
    ]
    for spec in specs:
        if db.query(CrawlTask).filter(CrawlTask.name == spec["name"]).one_or_none() is not None:
            continue
        sites = db.query(SeedSite).filter(SeedSite.domain.in_(spec["site_ids"])).all()
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
            name=spec["name"],
            site_ids=json.dumps(spec["site_ids"]),
            concurrency=spec["concurrency"],
            quota_snapshot=json.dumps(quota_snapshot, ensure_ascii=False),
            status=spec["status"],
            seed=spec["seed"],
            window_s=spec["window_s"],
            max_sequence=spec["max_sequence"],
            scheduled_count=0,
            created_by=spec["created_by"],
        )
        db.add(task)
        db.flush()
        if spec["simulate"]:
            configs = _site_configs(db, spec["site_ids"])
            urls = _queued_urls(db, spec["site_ids"])
            if configs and urls:
                result = scheduler.simulate(
                    configs,
                    urls,
                    task_name=spec["name"],
                    window_s=spec["window_s"],
                    max_sequence=spec["max_sequence"],
                    seed=spec["seed"],
                    now=BASE_UTC,
                )
                task.scheduler_result = json.dumps(result, ensure_ascii=False)
                task.scheduled_count = result["sequence_length"]
                task.status = TaskStatus.FINISHED.value
                task.started_at = BASE_UTC
                task.finished_at = BASE_UTC + timedelta(seconds=result["elapsed_s"])
        db.add(task)
    db.commit()
    return db.query(CrawlTask).order_by(CrawlTask.created_at.asc()).all()


RATE_LIMITED_INDICES = {23, 61, 97, 140, 188, 233, 274, 311, 356, 398, 437, 478}
FETCH_WEIGHTS = [
    "www.toutiao.com",
    "www.toutiao.com",
    "www.toutiao.com",
    "www.thepaper.cn",
    "www.thepaper.cn",
    "www.36kr.com",
    "www.jiemian.com",
    "finance.sina.com.cn",
]


def _seed_fetches(db: Session, tasks: list[CrawlTask]) -> int:
    existing = db.query(FetchRecord).filter(FetchRecord.origin == FetchOrigin.SEED.value).count()
    if existing:
        return 0
    sites = {site.domain: site for site in db.query(SeedSite).all()}
    urls_by_domain: dict[str, list[FrontierUrl]] = {}
    done_by_domain: dict[str, list[FrontierUrl]] = {}
    for row in db.query(FrontierUrl).filter(FrontierUrl.is_duplicate.is_(False)).all():
        site = next((site for site in sites.values() if site.id == row.site_id), None)
        if site is None:
            continue
        urls_by_domain.setdefault(site.domain, []).append(row)
        if row.status == UrlStatus.DONE.value:
            done_by_domain.setdefault(site.domain, []).append(row)
    for rows in urls_by_domain.values():
        rows.sort(key=lambda item: item.raw_url)
    for rows in done_by_domain.values():
        rows.sort(key=lambda item: item.raw_url)

    task_cycle = [task for task in tasks] or [None]
    inserted = 0
    for index in range(500):
        domain = FETCH_WEIGHTS[_stable_int("domain", index) % len(FETCH_WEIGHTS)]
        candidates = done_by_domain.get(domain) or urls_by_domain.get(domain) or []
        if not candidates:
            continue
        url = candidates[_stable_int("url", index) % len(candidates)]
        task = task_cycle[_stable_int("task", index) % len(task_cycle)] if task_cycle else None
        rate_limited = index in RATE_LIMITED_INDICES
        if rate_limited:
            status_code = 429
            backoff = 5.0 * (2 ** ((index // 100) % 3))
        else:
            bucket = _stable_int("code", index) % 100
            if bucket < 78:
                status_code = 200
            elif bucket < 90:
                status_code = 304
            elif bucket < 97:
                status_code = 404
            else:
                status_code = 500
            backoff = 0.0
        db.add(
            FetchRecord(
                task_id=task.id if task else None,
                url_id=url.id,
                domain=domain,
                status_code=status_code,
                latency_ms=80 + _stable_int("lat", index) % 900,
                bytes=2048 + _stable_int("bytes", index) % 200000,
                was_duplicate=_stable_int("dup", index) % 27 == 0,
                rate_limited=rate_limited,
                backoff_applied_s=backoff,
                origin=FetchOrigin.SEED.value,
                fetched_at=BASE_UTC + timedelta(seconds=index * 7),
            )
        )
        inserted += 1
    db.commit()
    return inserted


def _seed_audits(db: Session) -> int:
    created = 0
    specs = [
        ("www.toutiao.com", "2026-11-10T06:00", AUDIT_BASE_UTC),
        ("www.thepaper.cn", "2026-11-10T07:30", AUDIT_BASE_UTC + timedelta(hours=1, minutes=30)),
    ]
    for domain, batch_label, created_at in specs:
        existing = (
            db.query(CoverageAudit)
            .filter(CoverageAudit.site_domain == domain, CoverageAudit.batch_label == batch_label)
            .one_or_none()
        )
        if existing is not None:
            continue
        coverage_service.run_audit(
            db,
            site_domain=domain,
            batch_label=batch_label,
            now=created_at,
            skip_if_exists=True,
        )
        created += 1
    return created


def _summary(db: Session) -> dict:
    sites = db.query(SeedSite).count()
    urls = db.query(FrontierUrl).count()
    unique = db.query(FrontierUrl).filter(FrontierUrl.is_duplicate.is_(False)).count()
    tasks = db.query(CrawlTask).count()
    fetches = db.query(FetchRecord).filter(FetchRecord.origin == FetchOrigin.SEED.value).count()
    audits = db.query(CoverageAudit).count()
    users = db.query(User).count()
    return {
        "brand": BRAND,
        "sites": sites,
        "urls": urls,
        "unique": unique,
        "tasks": tasks,
        "fetches": fetches,
        "audits": audits,
        "users": users,
    }


SEED_SUMMARY_FIELDS = ("brand", "sites", "urls", "unique", "tasks", "fetches", "audits", "users")


def format_seed_summary(summary: dict) -> str:
    body = " ".join(f"{field}={summary[field]}" for field in SEED_SUMMARY_FIELDS)
    return f"SEED_SUMMARY {body}"


def seed_all() -> dict:
    db = SessionLocal()
    try:
        created_users = _seed_users(db)
        sites = _seed_sites(db)
        frontier = _seed_frontier(db, sites)
        tasks = _seed_tasks(db)
        created_fetches = _seed_fetches(db, tasks)
        created_audits = _seed_audits(db)
        summary = _summary(db)
        line = format_seed_summary(summary)
        print(line, flush=True)
        logger.warning("[SEED_DEMO] %s", line)
        return {
            "created_users": created_users,
            "frontier": frontier,
            "created_fetches": created_fetches,
            "created_audits": created_audits,
            **{key: summary[key] for key in ("sites", "urls", "unique", "tasks", "fetches", "audits", "users")},
        }
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover - 手动调试入口
    seed_all()
