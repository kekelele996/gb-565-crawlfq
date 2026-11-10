from __future__ import annotations

from pydantic import BaseModel, Field


class AuditRunRequest(BaseModel):
    site_domain: str = Field(min_length=3, max_length=160)
    batch_label: str | None = None
