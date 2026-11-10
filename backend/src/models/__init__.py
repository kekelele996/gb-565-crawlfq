"""模型注册表（init_db 依赖这里的导入顺序）。"""
from __future__ import annotations

from src.models.audit_log import AuditLog
from src.models.base import Base, TimestampMixin, new_uuid, utcnow
from src.models.coverage_audit import CoverageAudit
from src.models.crawl_task import CrawlTask
from src.models.fetch_record import FetchRecord
from src.models.frontier_url import FrontierUrl
from src.models.seed_site import SeedSite
from src.models.user import User

__all__ = [
    "AuditLog",
    "Base",
    "CoverageAudit",
    "CrawlTask",
    "FetchRecord",
    "FrontierUrl",
    "SeedSite",
    "TimestampMixin",
    "User",
    "new_uuid",
    "utcnow",
]
