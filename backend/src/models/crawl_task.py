from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid


class CrawlTask(Base, TimestampMixin):
    """采集任务：站点集合 + 调度参数 + 最近一次调度模拟结果（JSON 文本）。"""

    __tablename__ = "crawl_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    site_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    quota_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    window_s: Mapped[float] = mapped_column(Float, nullable=False, default=20.0)
    max_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    scheduled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scheduler_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
