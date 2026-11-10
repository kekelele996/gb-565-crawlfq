"""Celery 应用（worker 使用；backend 仅共享配置与队列名）。"""
from __future__ import annotations

from celery import Celery

from src.config.settings import settings

celery_app = Celery(
    "crawlfq",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    worker_hijack_root_logger=False,
)
