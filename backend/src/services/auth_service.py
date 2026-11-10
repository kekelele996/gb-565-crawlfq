"""认证服务：登录、JWT 签发、用户序列化（含权限清单）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.roles import ROLE_LABELS, role_permissions
from src.models.user import User
from src.utils.errors import AppError
from src.utils.jwt import create_access_token
from src.utils.password import verify_password
from src.utils.timeutil import to_iso, utcnow


def serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, user.role),
        "permissions": role_permissions(user.role),
        "is_active": user.is_active,
        "last_login_at": to_iso(user.last_login_at),
    }


def authenticate(db: Session, email: str, password: str) -> User:
    normalized = (email or "").lower().strip()
    user = db.query(User).filter(User.email == normalized).one_or_none()
    if user is None or not verify_password(password or "", user.password_hash):
        raise AppError(codes.AUTH_INVALID, "邮箱或密码不正确", f"email={normalized}")
    if not user.is_active:
        raise AppError(codes.FORBIDDEN, "账号已停用", f"user_id={user.id}")
    user.last_login_at = utcnow()
    db.add(user)
    return user


def issue_token(user: User) -> dict:
    return {
        "access_token": create_access_token(user),
        "token": create_access_token(user),
        "token_type": "bearer",
        "expires_in": settings.access_token_minutes * 60,
        "user": serialize_user(user),
    }
