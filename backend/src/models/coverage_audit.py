from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid


class CoverageAudit(Base, TimestampMixin):
    """覆盖度审计：sitemap 声明 / 已发现 / 已抓 / 覆盖率 / 缺口明细（JSON）。"""

    __tablename__ = "coverage_audits"
    __table_args__ = (UniqueConstraint("site_domain", "batch_label", name="uq_audit_site_batch"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    site_domain: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    batch_label: Mapped[str] = mapped_column(String(64), nullable=False)
    sitemap_declared: Mapped[int] = mapped_column(Integer, nullable=False)
    discovered: Mapped[int] = mapped_column(Integer, nullable=False)
    fetched: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    gap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gaps: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
