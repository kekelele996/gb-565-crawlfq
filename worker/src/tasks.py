"""worker 任务：写心跳 + 周期性清理过期调度模拟抓取记录（演示用）。"""
from __future__ import annotations

import time

import redis

from src.config.celery_app import celery_app
from src.config.settings import settings

HEARTBEAT_KEY = "crawlfq:worker:heartbeat"


@celery_app.task(name="worker_src.tasks.heartbeat", ignore_result=True)
def heartbeat() -> str:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    client.set(HEARTBEAT_KEY, str(time.time()), ex=120)
    return "ok"


@celery_app.task(name="worker_src.tasks.probe_db")
def probe_db() -> int:
    """轻量连通性任务：返回队列等待中的 URL 数（演示 worker 读取共享 DB）。"""
    from sqlalchemy import func

    from src.config.database import SessionLocal
    from src.models.frontier_url import FrontierUrl

    db = SessionLocal()
    try:
        return int(
            db.query(func.count(FrontierUrl.id))
            .filter(FrontierUrl.status == "queued", FrontierUrl.is_duplicate.is_(False))
            .scalar()
            or 0
        )
    finally:
        db.close()
