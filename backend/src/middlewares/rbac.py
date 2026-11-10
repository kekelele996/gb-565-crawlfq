"""RBAC：按权限点声明式鉴权（viewer 调高权接口返回 403）。"""
from __future__ import annotations

from fastapi import Depends

from src.constants import error_codes as codes
from src.constants.roles import PERMISSIONS, ROLE_LABELS
from src.middlewares.auth import get_current_user
from src.models.user import User
from src.utils.errors import AppError


def require_permission(permission: str):
    roles = PERMISSIONS.get(permission, ())

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise AppError(
                codes.FORBIDDEN,
                f"{ROLE_LABELS.get(user.role, user.role)}没有「{permission}」权限",
                f"role={user.role} permission={permission}",
                extra={"permission": permission, "role": user.role},
            )
        return user

    return Depends(dependency)
