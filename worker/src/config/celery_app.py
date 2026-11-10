"""Celery 应用：worker 心跳任务 + 周期性写 Redis 键供 healthcheck 判定。"""
from __future__ import annotations

from celery import Celery
from celery.schedules import schedule

from src.config.settings import settings

celery_app = Celery("crawlfq_worker", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    worker_hijack_root_logger=False,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "worker-heartbeat": {
            "task": "worker_src.tasks.heartbeat",
            "schedule": schedule(run_every=15.0),
        }
    },
)

celery_app.autodiscover_tasks(["worker_src"], related_name="tasks", force=True)
