from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid


class SeedSite(Base, TimestampMixin):
    """采集站点（域）与礼貌配额配置。"""

    __tablename__ = "seed_sites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    domain: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    robots_status: Mapped[str] = mapped_column(String(16), nullable=False, default="allow")
    robots_rules: Mapped[str] = mapped_column(
        Text, nullable=False, default='{"disallow": [], "allow": []}'
    )
    crawl_delay_s: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    qps_quota: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    sitemap_declared: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_audited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
