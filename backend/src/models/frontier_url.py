from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid


class FrontierUrl(Base, TimestampMixin):
    """URL 前沿条目：原始 URL + 规范化 URL + sha256 指纹 + 折叠关系。"""

    __tablename__ = "frontier_urls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    raw_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="sitemap")
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)
    wait_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    folded_into_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    change_reasons: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
