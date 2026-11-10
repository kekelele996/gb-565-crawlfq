"""共享枚举（后端唯一真源）；前端 src/constants/enums.ts 保持字面量一致。

README「枚举出现位置」列出全部引用点。
"""
from __future__ import annotations

from enum import Enum


class RobotsStatus(str, Enum):
    """共享枚举 #1：站点 robots 策略。"""

    ALLOW = "allow"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class UrlStatus(str, Enum):
    """共享枚举 #2：前沿 URL 状态。

    folded = 被规范化指纹折叠的重复变体行（保留原始 raw_url 供对比展示）。
    """

    QUEUED = "queued"
    INFLIGHT = "inflight"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"
    FOLDED = "folded"


class UrlSource(str, Enum):
    """共享枚举 #3：URL 发现来源。"""

    SITEMAP = "sitemap"
    LINK = "link"
    SEED = "seed"


class TaskStatus(str, Enum):
    """共享枚举 #4：采集任务状态机 queued/running/paused/finished。"""

    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"


class FetchOrigin(str, Enum):
    """共享枚举 #5：抓取记录来源（seed 演示 / simulation 调度模拟）。"""

    SEED = "seed"
    SIMULATION = "simulation"


class GapReason(str, Enum):
    """共享枚举 #6：sitemap 缺口原因（覆盖度审计导出 CSV 的 reason 列）。"""

    NOT_DISCOVERED = "not_discovered"
    ROBOTS_BLOCKED = "robots_blocked"
    FETCH_FAILED = "fetch_failed"
    OVER_QUOTA = "over_quota"


class SignalLevel(str, Enum):
    """共享枚举 #7：令牌桶信号灯（绿/黄/红，塔台进近图配色）。"""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class UserRole(str, Enum):
    """共享枚举 #8：账号角色。"""

    ADMIN = "admin"
    ENGINEER = "engineer"
    VIEWER = "viewer"


URL_STATUS_ORDER: tuple[str, ...] = (
    UrlStatus.QUEUED.value,
    UrlStatus.INFLIGHT.value,
    UrlStatus.DONE.value,
    UrlStatus.BLOCKED.value,
    UrlStatus.FAILED.value,
    UrlStatus.FOLDED.value,
)

TASK_TRANSITIONS: dict[str, tuple[str, ...]] = {
    TaskStatus.QUEUED.value: (TaskStatus.RUNNING.value, TaskStatus.PAUSED.value),
    TaskStatus.RUNNING.value: (TaskStatus.PAUSED.value, TaskStatus.FINISHED.value),
    TaskStatus.PAUSED.value: (TaskStatus.RUNNING.value, TaskStatus.FINISHED.value),
    TaskStatus.FINISHED.value: (),
}

GAP_REASON_LABELS: dict[str, str] = {
    GapReason.NOT_DISCOVERED.value: "sitemap 未发现",
    GapReason.ROBOTS_BLOCKED.value: "robots 禁止路径",
    GapReason.FETCH_FAILED.value: "抓取失败",
    GapReason.OVER_QUOTA.value: "配额耗尽未抓",
}
