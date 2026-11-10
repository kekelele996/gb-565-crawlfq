"""RBAC：三角色 admin / engineer / viewer。

前后端必须一致：users.role / constants/roles.py / frontend/src/constants/enums.ts。
viewer 只读：创建任务、运行调度模拟、改站点配额、跑审计、导出缺口全部 403。
"""
from __future__ import annotations

from src.constants.enums import UserRole

ROLE_ADMIN = UserRole.ADMIN.value
ROLE_ENGINEER = UserRole.ENGINEER.value
ROLE_VIEWER = UserRole.VIEWER.value

ALL_ROLES: tuple[str, ...] = (ROLE_ADMIN, ROLE_ENGINEER, ROLE_VIEWER)

PERMISSIONS: dict[str, tuple[str, ...]] = {
    "sites:read": ALL_ROLES,
    # 只有调度主管能改 qps / crawl-delay / 并发 / 优先级 / 启停
    "sites:update": (ROLE_ADMIN,),
    "frontier:read": ALL_ROLES,
    # 规范化试算是纯计算，只读角色也可用
    "frontier:preview": ALL_ROLES,
    "tasks:read": ALL_ROLES,
    "tasks:create": (ROLE_ADMIN, ROLE_ENGINEER),
    "tasks:simulate": (ROLE_ADMIN, ROLE_ENGINEER),
    "fetches:read": ALL_ROLES,
    "audits:read": ALL_ROLES,
    "audits:run": (ROLE_ADMIN, ROLE_ENGINEER),
    "audits:export": (ROLE_ADMIN, ROLE_ENGINEER),
    "audit:read": (ROLE_ADMIN,),
    "users:admin": (ROLE_ADMIN,),
}

ROLE_LABELS: dict[str, str] = {
    ROLE_ADMIN: "调度主管",
    ROLE_ENGINEER: "采集工程师",
    ROLE_VIEWER: "只读观察员",
}


def role_permissions(role: str) -> list[str]:
    return sorted(permission for permission, roles in PERMISSIONS.items() if role in roles)
