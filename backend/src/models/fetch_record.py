from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid


class FetchRecord(Base, TimestampMixin):
    """抓取记录：状态码、耗时、字节数、是否重复、是否 429、退避秒数。"""

    __tablename__ = "fetch_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    url_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    domain: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    was_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rate_limited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    backoff_applied_s: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="seed", index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
