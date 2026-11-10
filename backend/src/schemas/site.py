from __future__ import annotations

from pydantic import BaseModel


class SiteUpdateRequest(BaseModel):
    qps_quota: float | None = None
    crawl_delay_s: float | None = None
    max_concurrency: int | None = None
    priority: int | None = None
    enabled: bool | None = None
    robots_status: str | None = None
    robots_rules: dict | None = None
